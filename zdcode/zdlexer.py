import re
import sys
import os
import traceback
import parsy

from parsy import generate, string, regex, seq, whitespace, success, fail


s = string
fa = fail
wo = whitespace.optional()

def istring(st):
    return s(st, transform=lambda s: s.upper())

ist = istring

string_body_1 = regex(r'[^"\\]+')
string_body_2 = regex(r'[^\'\\]+')
string_esc = string('\\') >> (
    string('\\')
    | string('/')
    | string('"')
    | string('b').result('\b')
    | string('f').result('\f')
    | string('n').result('\n')
    | string('r').result('\r')
    | string('t').result('\t')
    | regex(r'u[0-9a-fA-F]{4}').map(lambda s: chr(int(s[1:], 16)))
    | regex(r'x[0-9a-fA-F]{2}').map(lambda s: chr(int(s[1:], 16)))
)
string_delim_1 = s('"')
string_delim_2 = s("'")
string_body_plex_1 = (string_body_1 | string_esc).many().concat()
string_body_plex_2 = (string_body_2 | string_esc).many().concat()
string_literal = (
    (string_delim_1 >> string_body_plex_1 << string_delim_1)
    | (string_delim_2 >> string_body_plex_2 << string_delim_2)
)
lwhitespace = whitespace | s('\n') | s('\r')

ifneq = re.compile(r'^\#IF(N|NOT)EQ(UALS?)?$')
ifundef = re.compile(r'^\#IF(U?N|NOT)DEF(INED)?$')
defmacro = re.compile(r'^\#DEF(INE)?M(AC(RO)?)?$')

error_line = re.compile(r'(.+?) at (\d+)\:(\d+)$')

class PreprocessingError(BaseException):
    def __init__(self, problem, line, fname = None, line_content = None):
        self.problem = problem
        self.error_line = line
        self.filename = fname
        self.line_content = line_content

    def __str__(self):
        return "{} (line {} {}){}".format(self.problem, self.error_line, 'of input code' if self.filename is None else 'in "{}"'.format(self.filename), '' if self.line_content is None else ':\n> ' + self.line_content)

class ZDParseError(BaseException):
    def __init__(self, parsy_error: parsy.ParseError, postline=None):
        self.parsy_error = parsy_error
        self.postline = postline

    def __str__(self):
        filename = self.postline[0]
        error_line = self.postline[1]
        line_source = self.postline[2]

        return "expected one of {} at line {}{} {}:\n> {}\n{}^".format(', '.join(repr(l) for l in self.parsy_error.expected), error_line, ':' + str(self.parsy_error.index - self.postline[4]), 'of input code' if filename is None else 'in "{}"'.format(filename), line_source, ' ' * max(0, self.parsy_error.index - self.postline[4] + 2))

@generate
def modifier():
    return string('[').then(regex('[a-zA-Z\(\)0-9]+').desc('modifier body')).skip(s(']'))
    yield

def _apply_replacements(expr, replacements):
    res = []

    for item in expr:
        if item in replacements:
           res.append(replacements[item])

        else:
            res.append(item)

    return ' '.join(res)

def apply_replacements(expr, replacements):
    return _apply_replacements(expression.parse(expr), replacements)

@generate
def number_lit():
    return (
            regex(r'[\+\-]?\d+(.\d+)?(e[\+\-]?\d+)?').tag('number')
        |   regex(r'0x[0-9A-Fa-f]+').map(int).tag('number')
        |   regex(r'0b[01]+').map(int).tag('number')
        )
    yield

@generate
def literal():
    return (
        call_literal.tag('call expr').desc('call') |
        string_literal.tag('string').desc('string') |
        regex(r'[a-zA-Z_][a-zA-Z0-9_\[\]]*').tag('actor variable').desc('actor variable') |
        number_lit.desc('number')
    )
    yield

@generate
def array_literal():
    return (wo >> s('{') >> wo >> expression.sep_by(s(',') << wo) << s('}')).tag('array')
    yield

@generate
def paren_expr():
    return s('(') >> expression << s(')')
    yield

@generate
def expression():
    return (
        (
            wo >>
            (
                (
                    paren_expr.tag('paren expr').desc('parenthetic expression') |
                    literal.tag('literal') |
                    regex(r'[\+\-\|\>\<\~\&\!\=\*\/\%\[\]]+').desc('operator').tag('oper')
                ).sep_by(wo).tag('expr')
            )
            << wo
        ) | (wo >> paren_expr.tag('paren expr') << wo)
    )
    yield


@generate
def arg_expression():
    return parameter.tag('position arg') | seq(parameter, regex(r'[\:\,]') >> wo >> expression).tag('named arg')
    yield

@generate
def argument_list():
    return (literal).sep_by(regex(r',\s*'))
    yield

@generate
def macro_argument_list():
    return wo >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('macro argument name').sep_by(regex(r',\s*')) << wo
    yield

@generate
def template_parameter_list():
    return wo >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('template parameter name').sep_by(regex(r',\s*')) << wo
    yield

@generate
def expr_argument_list():
    return arg_expression.sep_by(regex(r',\s*'))
    yield

@generate
def parameter():
    return anonymous_class | templated_class_derivation | expression.tag('expression')
    yield

def specialized_parameter_list(ptype):
    @generate
    def plist():
        return ptype.sep_by(regex(r',\s*'))
        yield

    return plist

parameter_list = specialized_parameter_list(parameter)

@generate
def actor_function_call():
    return ist('call ').desc("'call' statement").then(regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called function name'))
    yield

@generate
def state_call():
    return seq(
        regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called state function name').skip(wo),
        s('(').then(wo).then(
            expr_argument_list
        ).skip(wo).skip(s(')')).optional()
    )
    yield

@generate
def return_statement():
    return (wo >> ist('return')).desc('return statement')
    yield

@generate
def call_literal():
    return seq(
        regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called expression function name') << wo,
        (s('(') >> wo >>
            expr_argument_list
        << wo << s(')'))
    )
    yield

@generate
def label():
    return (seq(((ist("label") | ist('state')) << whitespace) >> regex('[a-zA-Z_]+').desc('label name').tag('name'), state_body.tag('body')).map(dict) << wo)
    yield

@generate
def templated_class_derivation():
    return seq(
        regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('name of templated class') << wo,
        (s('::(') >> wo >>
            parameter_list.optional().map(lambda x: x if x and tuple(x) != ('',) else [])
        << wo << s(')')),
        (
            wo >> s('{') >>
                wo.then(
                    (((ist('is') << whitespace) | string("+")) >> regex('[a-zA-Z0-9_]+').desc('flag name')).tag('flag') |
                    (((ist("isn't") << whitespace) | string('-')) >> regex('[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag') |

                    seq(
                        ist("macro") >> whitespace >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
                        (wo >> s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []).tag('args'),
                        state_body.tag('body')
                    ).map(dict).desc('override macro').tag('macro') |

                    label.desc('ovveride label').tag('label') |

                    ((ist('var') << whitespace) >> seq(
                        regex('user_[a-zA-Z0-9_]+').desc('var name').tag('name'),
                        (wo >> s('[') >> replaceable_number << s(']')).optional().map(lambda x: int(x or 0)).tag('size'),
                        (wo >> s(':') >> wo >> regex('[a-zA-Z_.][a-zA-Z0-9_]+')).desc('var type').optional().map(lambda t: t or 'int').tag('type'),
                        (wo >> s('=') >> (expression.tag('val') | array_literal.tag('arr'))).optional().tag('value')
                    ).map(dict).tag('user var')) |

                    ((ist('array') << whitespace) >> seq(
                        regex('user_[a-zA-Z0-9_]+').desc('array name').tag('name'),
                        (wo >> s('=') >> wo >> array_literal).desc('array values').tag('value')
                    ).map(dict).desc('override array').tag('array'))
                ).skip(wo).skip(s(';')).skip(wo).many().optional()
            << s('}')
        ).optional().map(lambda x: x or [])
    ).tag('template derivation').desc('template derivation')
    yield

@generate
def static_template_derivation():
    return wo >> seq(
        ist('derive') >> whitespace >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('name of derived class').tag('classname'),
        whitespace >> ist('as') >> whitespace >> templated_class_derivation.tag('source'),
    ).desc('static template derivation') << s(';') << wo
    yield

@generate
def class_body():
    return wo.then(
            seq(
                ist("macro") >> whitespace >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
                (wo >> s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []).tag('args'),
                state_body.tag('body')
            ).map(dict).tag('macro') |
            seq(
                (ist('set') >> whitespace).desc("'set' keyword") >> regex('[a-zA-Z0-9_]+').tag('name'),
                ((whitespace >> ist('to') << whitespace) | (wo >> s('=') << wo)).desc("'to' or equal sign") >> parameter.sep_by((s(',') << wo)).tag('value')
            ).map(dict).tag('property') |
            (((ist('is') << whitespace) | string("+")) >> regex('[a-zA-Z0-9_]+').desc('flag name')).tag('flag') |
            (ist('var') << whitespace) >> seq(
                regex('user_[a-zA-Z0-9_]+').desc('var name').tag('name'),
                (wo >> s('[') >> replaceable_number << s(']')).desc('array size').optional().map(lambda x: int(x or 0)).tag('size'),
                (wo >> s(':') >> wo >> regex('[a-zA-Z_.][a-zA-Z0-9_]+')).desc('var type').optional().map(lambda t: t or 'int').tag('type'),
                (wo >> s('=') >> (expression.tag('val') | array_literal.tag('arr'))).optional().tag('value')
            ).map(dict).tag('user var') |
            (((ist("isn't") << whitespace) | string('-')) >> regex('[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag') |
            (ist('combo') >> whitespace >> regex('[a-zA-Z0-9_]+').desc('combo name')).tag('flag combo') |
            seq((ist("function ") | ist('method ')) >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('function name').tag('name'), state_body.tag('body')).map(dict).tag('function') |
            label.tag('label')
    ).skip(wo) << s(';') << wo
    yield

@generate
def abstract_label_body():
    return (ist("abstract label") | ist('abstract state')) >> whitespace >> regex('[a-zA-Z_]+').desc('label name') << s(';')
    yield

@generate
def abstract_array_body():
    return seq(
        ist("abstract array") >> whitespace >> regex('user_[a-zA-Z0-9_]+').desc('array name').tag('name'),
        (wo >> s('[') >> replaceable_number << s(']')).optional().map(lambda x: int(x) if x else 'any').tag('size'),
        (wo >> s(':') >> wo >> regex('[a-zA-Z_.][a-zA-Z0-9_]+')).desc('var type').optional().map(lambda t: t or 'int').tag('type')
    ).map(dict) << wo << s(';') << wo
    yield

@generate
def abstract_macro_body():
    return seq(
        ist("abstract macro") >> whitespace >> regex('[a-zA-Z_]+').desc('macro name').tag('name') << wo,
        (s('(') >> wo >> macro_argument_list << wo << s(')')).optional().map(lambda x: x or []).tag('args')
    ).map(dict) << wo << s(';') << wo
    yield

@generate
def sprite_name():
    return (
        (regex(r'[A-Z0-9_]{4}') | s('"#"')).tag('normal') |
        (ist('param') >> whitespace >> regex('[a-zA-Z_][a-zA-Z_0-9]*')).tag('parametrized')
    )
    yield

@generate
def superclass():
    return (
        templated_class_derivation |
        regex('[a-zA-Z][a-zA-Z0-9_]+').tag('classname')
    )
    yield

@generate
def actor_class():
    return seq(
        ((ist('actor') | ist('class')) << whitespace).desc("class statement") >> regex('[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((whitespace >> (ist('inherits') | ist('extends') | ist('expands'))) >> whitespace >> superclass.desc('inherited class')).optional().tag('inheritance').desc('inherited class name'),
        (whitespace >> (ist('replaces') >> whitespace >> regex('[a-zA-Z0-9_]+'))).desc('replaced class name').optional().tag('replacement').desc('replacement'),
        (whitespace >> s('#') >> regex('[0-9]+')).desc('class number').map(int).optional().tag('class number').desc('class number').skip(wo),

        (s('{') >> wo >> class_body.many().optional() << wo.then(s('}')).skip(wo)).tag('body')
    )
    yield

@generate
def templated_actor_class():
    return seq(
        (ist('actor') | ist('class') | ist('template')).desc("class template") >> s('<') >> template_parameter_list.tag('parameters') << s('>') << wo,
        regex('[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((whitespace >> (ist('inherits') | ist('extends') | ist('expands'))) >> whitespace >> superclass.desc('inherited class')).optional().tag('inheritance').desc('inherited class name'),
        (whitespace >> (ist('replaces') >> whitespace >> regex('[a-zA-Z0-9_]+'))).desc('replaced class name').optional().tag('replacement').desc('replacement'),
        (whitespace >> s('#') >> regex('[0-9]+')).desc('class number').map(int).optional().tag('class number').desc('class number').skip(wo),

        (s('{') >> wo >> (abstract_macro_body.desc('abstract macro').tag('abstract macro') | abstract_array_body.desc('abstract array').tag('abstract array') | abstract_label_body.desc('abstract label').tag('abstract label') | class_body).many().optional() << wo.then(s('}')).skip(wo)).tag('body')
    )
    yield

@generate
def anonymous_class():
    return seq(
        (ist('actor') | ist('class')).desc("class statement") >> \
                whitespace >> \
                (
                    (ist('inherits') | ist('extends') | ist('expands')).desc('inheritance declaration') >> \
                    whitespace >> \
                    superclass
                ).desc('inherited class name').optional().tag('inheritance') <<
                wo,

        (
            ist('{') >>
            wo >>
            class_body.many().optional() <<
            wo <<
            ist('}') <<
            wo
        ).optional().map(lambda x: x or []).tag('body')
    ).tag('anonymous class')
    yield

@generate
def normal_state():
    return seq(
        sprite_name.desc('state name').skip(wo),
        (regex(r"[A-Z_.]").many() | s('"#"')).desc('state sprite').skip(wo),
        regex(r"\-?\d+").map(int).desc('state duration').skip(wo),
        modifier.many().desc('modifier').skip(wo).optional(),
        state_action.optional()
    ) | seq(
        ist('keepst').desc('\'keepst\' state').skip(wo) >>\
        regex(r"\-?\d+").map(int).desc('state duration').skip(wo),
        modifier.many().desc('modifier').skip(wo).optional(),
        state_action.optional()
    ).map(lambda l: [('normal', '"####"'), '"#"', *l]) | seq(
        ist('invisi').desc('\'invisi\' state').skip(wo) >>\
        regex(r"\-?\d+").map(int).desc('state duration').skip(wo),
        modifier.many().desc('modifier').skip(wo).optional(),
        state_action.optional()
    ).map(lambda l: [('normal', 'TNT1'), 'A', *l])
    yield

@generate
def pure_action_state():
    return seq(
        ist('keep') >> whitespace >> (regex(r"\-?\d+").map(int).desc('state duration').optional().map(lambda x: x or 0)).skip(
            wo
        ),
        modifier.many().desc('modifier').skip(
            wo
        ).optional(),
        state_action.optional()
    )
    yield

@generate
def state_action():
    return action_body_repeat.tag('inline body') | state_call.tag('action') | action_body.tag('inline body')
    yield

@generate
def action_body():
    return s('{') >> wo >> (state_action << s(';') << wo).many().optional() << s('}')
    yield

@generate
def replaceable_number():
    return (
        regex(r'\d+').map(int) |
        regex('[a-zA-Z_][a-zA-Z_0-9]*')
    )
    yield

@generate
def action_body_repeat():
    return seq(
        ist('x') >> wo >> replaceable_number.desc('amount of times to repeat') << wo, state_action
    ).map(lambda x: [x[1] for _ in range(x[0])])
    yield

@generate
def flow_control():
    return (ist('stop') | ist('wait') | ist('fail') | ist('loop') | ist('goto') + whitespace.map(lambda _: ' ') + regex(r'[a-zA-Z0-9\:\.]+\s?(?:\+\d+)?'))
    yield

@generate
def macro_call():
    return seq(
        ist('inject').desc("'inject' statement").then(whitespace).then(regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('injected macro name')),
        (s('(') >> expr_argument_list.desc("macro arguments") << s(')')).optional().map(lambda x: x or [])
    )
    yield

@generate
def state():
    return (if_statement.tag('if') | sometimes_statement.tag('sometimes') | while_statement.tag('while') | actor_function_call.tag('call') | macro_call.tag('inject') | flow_control.tag('flow') | normal_state.tag('frames') | repeat_statement.tag('repeat')) << s(';')
    yield

@generate
def state_no_colon():
    return (if_statement.tag('if') | sometimes_statement.tag('sometimes') | while_statement.tag('while') | actor_function_call.tag('call') | macro_call.tag('inject') | flow_control.tag('flow') | normal_state.tag('frames') | repeat_statement.tag('repeat'))
    yield

@generate
def state_body():
    return (
        (state_no_colon | return_statement.tag('return')).map(lambda x: [x])
        | (
            wo >> string("{") >> wo >> (
                state | (return_statement << ';').tag('return')
            ).sep_by(wo) << wo << string("}")
        )
    )
    yield

@generate
def sometimes_statement():
    return seq(
        s('sometimes') >>\
                whitespace >>\
                (s('(') >> wo >> expression << wo << s(')') | replaceable_number.map(lambda r: ('expr', [('literal', (('number' if type(r) is int else 'actor variable'), r))]))).tag('chance') <<\
                s('%').optional() <<
                wo,
        state_body.optional().map(lambda x: x if x != None else []).tag('body')
    )
    yield

@generate
def if_statement():
    return seq(
        ist("if").desc('if statement')
        .then(wo)
        .then(string("("))
        .then(wo)
            .then(expression)
        .skip(wo)
        .skip(string(")"))
        .skip(wo),

        state_body.optional().map(lambda x: x if x != None else [])
        .skip(wo),

        s(';')
        .then(wo)
        .then(s('else'))
        .then(wo)
            .then(state_body.optional().map(lambda x: x if x != None else []))
        .skip(wo)
            .optional()
    )
    yield

@generate
def while_statement():
    return seq(
        ist("while").desc('while statement')
            .then(wo)
            .then(string("("))
            .then(wo)
            .then(expression)
        .skip(wo)
        .skip(string(")"))
        .skip(wo),
        state_body.optional().map(lambda x: x if x != None else [])
    )
    yield

@generate
def repeat_statement():
    return seq(
        ist('x') >> wo >> replaceable_number.desc('amount of times to repeat'),
        wo >> state_body
    )
    yield

@generate
def source_code():
    return wo.desc('ignored whitespace') >> (actor_class.tag('class') | static_template_derivation.tag('static template derivation') | templated_actor_class.tag('class template')).sep_by(wo) << wo.desc('ignored whitespace')
    yield

def rpcont(i=0):
    @generate
    def recursive_paren_content():
        return ((regex(r'[^\(\)]') if i else regex(r'[^\(\)\,]')) | (s('(') + rpcont(i+1)) + s(')')).many().concat()
        yield

    return recursive_paren_content

def preprocess_for_macros(code, defines=(), this_fname=None, i=0):
    l = code

    for key, (val, d_args) in defines.items():
        nl = ""

        while True:
            j = re.search(r'\b' + re.escape(key.upper()) + r'\(', l.upper())

            if not j:
                nl += l
                break

            j = j.start()
            nl += l[:j]
            l = l[j + len(key):]

            try:
                args, l = (s('(') >> rpcont().sep_by(s(',') << wo) << s(')')).parse_partial(l)
                args = [x for x in args if x]

            except parsy.ParseError as e:
                print('\n')
                traceback.print_exc()
                print()

                raise PreprocessingError("Unexpected error using parametrized preprocessor alias '{}'".format(key), i, this_fname, code + '\n\n')

            if len(d_args) != len(args):
                raise PreprocessingError("Bad number of arguments using parametrized preprocessor alias '{}': expected {}, got {}!".format(key, len(d_args), len(args)), i, this_fname, code)

            v = val

            for aname, aval in zip(d_args, args):
                ov = v
                v = re.sub('\({}\)'.format(re.escape(aname)), '({})'.format(aval), v)

            res = preprocess_for_macros(v, defines, this_fname, i)
            nl += res

        l = nl

    return l

def preprocess_code(code, imports=(), defs=(), defines=(), this_fname=None, rel_dir='.', begin_char=None):
    if not begin_char:
        begin_char = [0]

    if not isinstance(imports, list):
        imports = list(imports)

    if not isinstance(defs, dict):
        defs = dict(defs)

    if not isinstance(defines, dict):
        defines = dict(defines)

    # conditional substitution
    pcodelines = []

    cond_active = True
    depth = 0
    check_depth = 0

    # comments
    src_lines = code.split('\n')

    code = re.sub(r'\/\/[^\r\n]+', lambda x: re.sub(r'[^\n]', ' ', x.group(0)), code)
    code = re.sub(r'\/\*(\n|.)+?\*\/', lambda x: re.sub(r'[^\n]', ' ', x.group(0)), code)
    code = re.sub(r'\\\n', '', code)

    codelines = code.split('\n')

    for _i, l in enumerate(codelines):
        i = _i + 1
        src_l = src_lines[_i]

        check_line_case = re.sub(r'\s+', ' ', re.sub(r'^\s+', '', l))
        check_line = check_line_case.upper()

        # conditional blocks
        if check_line.startswith('#IFDEF ') or check_line.startswith('#IFDEFINED '):
            check_depth += 1

            if cond_active:
                key = check_line_case.split(' ')[1]

                if key not in defs:
                    cond_active = False

            else:
                depth += 1

        elif ifundef.match(check_line.split(' ')[0]):
            check_depth += 1

            if cond_active:
                key = check_line_case.split(' ')[1]

                if key in defs:
                    cond_active = False

            else:
                depth += 1

        elif check_line.startswith('#IFEQ ') or check_line.startswith('#IFEQUAL ') or check_line.startswith('#IFEQUALS '):
            check_depth += 1

            if cond_active:
                key = check_line_case.split(' ')[1]
                value = check_line_case.split(' ')[2:]

                if key not in defs or defs[key] != value:
                    cond_active = False

            else:
                depth += 1

        elif ifneq.match(check_line.split(' ')[0]):
            check_depth += 1

            if cond_active:
                key = check_line_case.split(' ')[1]
                value = check_line_case.split(' ')[2:]

                if key not in defs or defs[key] == value:
                    cond_active = False

            else:
                depth += 1

        elif check_line.startswith('#ELSE') or check_line.startswith('#OTHERWISE'):
            if check_depth == 0:
                raise PreprocessingError("Attempted to use 'else' on a conditional preprocessor block that didn't exist!", i, this_fname, check_line_case)

            cond_active = not cond_active

        elif check_line.startswith('#ENDIF'):
            check_depth -= 1

            if check_depth < 0:
                raise PreprocessingError("Attempted to end a conditional preprocessor block that didn't exist!", i, this_fname, check_line_case)

            if not cond_active:
                if depth > 0:
                    depth -= 1

                else:
                    cond_active = True

        # imports and definitions
        if cond_active:
            if check_line.startswith('#IMPORT ') or check_line.startswith('#INCLUDE '):
                fname = os.path.join(rel_dir, ' '.join(check_line_case.split(' ')[1:]))

                if not os.path.isfile(fname):
                    raise PreprocessingError("The module '{}' was not found".format(os.path.join(rel_dir, fname)), i, this_fname, check_line_case)

                if (this_fname, fname) in imports:
                    raise PreprocessingError("The module '{}' was found in an infinite import cycle!".format(fname), i, this_fname, check_line_case)

                imports.append((this_fname, fname))

                with open(fname) as fp:
                    lines = preprocess_code(fp.read() + "\n", imports, defs, defines, this_fname=fname, rel_dir=os.path.dirname(fname), begin_char=begin_char)

                    for l in lines:
                        pcodelines.append(l)

            elif check_line.startswith('#DEF ') or check_line.startswith('#DEFINE '):
                key = check_line_case.split(' ')[1]
                value = ' '.join(check_line_case.split(' ')[2:])

                if value == '':
                    defs[key] = None

                else:
                    defs[key] = value

            elif defmacro.match(check_line.split(' ')[0]):
                name = check_line_case.split(' ')[1]
                value = ' '.join(check_line_case.split(' ')[2:])

                (key, args), _ = seq(regex(r'[a-zA-Z_][a-zA-Z0-9_]*'), (s('(') >> (regex(r'[a-zA-Z_][a-zA-Z0-9_]*').sep_by(s(','))) << s(')')).optional().map(lambda x: x or [])).parse_partial(name)
                args = [x for x in args if x]

                if value == '':
                    raise PreprocessingError("Empty preprocessor macros ('{}') are not allowed!".format(key), i, this_fname, check_line_case)

                defs[key] = value
                defines[key] = (value, args)

            elif check_line.startswith('#UNDEF ') or check_line.startswith('#UNDEFINE '):
                key = check_line_case.split(' ')[1]

                if key in defs:
                    defs.pop(key)

                if key in defines:
                    defines.pop(key)

        if not check_line.startswith('#') and cond_active:
            l = preprocess_for_macros(l, defines, this_fname, i)
            src_l = preprocess_for_macros(src_l, defines, this_fname, i)

            pcodelines.append((this_fname, i, src_l, l, begin_char[0]))
            begin_char[0] += len(l) + 1

    return pcodelines

def parse_postcode(postcode, error_handler=None):
    try:
        lim = sys.getrecursionlimit()
        sys.setrecursionlimit(lim * 16)
        clazzes = source_code.parse('\n'.join(l[3] for l in postcode))
        sys.setrecursionlimit(lim)

        return ((x[0], dict(x[1])) for x in clazzes)

    except parsy.ParseError as parse_err:
        m = error_line.match(str(parse_err))

        if m is None:
            raise

        else:
            err = ZDParseError(parse_err, postcode[int(m[2])])

            if error_handler is None:
                raise err

            else:
                error_handler(err)

def parse_code(code, filename=None, dirname='.', error_handler=None):
    try:
        return parse_postcode(preprocess_code(code, this_fname=filename, rel_dir=dirname), error_handler=error_handler)

    except PreprocessingError as pperr:
        if error_handler is None:
            raise

        else:
            error_handler(pperr)
