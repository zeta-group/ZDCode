import re
import os
import parsy

from parsy import *


s = string
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

error_line = re.compile(r'(.+?) at (\d+)\:\d+$')

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

        return "{} at line {}{} {}:\n> {}\n{}^".format(str(self.parsy_error), error_line, ':' + str(self.parsy_error.index - self.postline[4]), 'of input code' if filename is None else 'in "{}"'.format(filename), line_source, ' ' * max(0, self.parsy_error.index - self.postline[4] + 2))

@generate
def modifier():
    return string('[').then(regex('[a-zA-Z\(\)0-9]+').desc('modifier body')).skip(s(']'))
    yield

def _parse_literal(literal):
    kind, val = literal

    if kind == 'number':
        return str(val)

    elif kind == 'string':
        return '"' + val + '"'

    elif kind == 'actor variable':
        return val

    elif kind == 'call expr':
        return _parse_action(val)

def _parse_action(a):
    name, args = a
    return "{}({})".format(name, '' if args is None else ', '.join(x for x in args))

def _apply_replacements(expr, replacements):
    res = []

    for item in expr:
        if item in replacements:
           res.append(replacements[item]) 

        else:
            res.append(item)

    return ' '.join(res)

def apply_replacements(expr, replacements):
    return _apply-replacements(expression.parse(expr), replacements)

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
def paren_expr():
    return s('(') + expression + s(')')
    yield

@generate
def expression():
    return (
        whitespace.optional() >>
        (
            (
                literal.map(_parse_literal) |
                regex(r'[\+\-\|\>\<\~\&\!\=\*\/\%x]+').desc('operator') |
                paren_expr.desc('parenthetic expression')
            ).sep_by(whitespace.optional()).map(lambda x: ' '.join(x))
        )
        << whitespace.optional()
    ) | paren_expr
    yield
    

@generate
def arg_expression():
    return (s('-').optional().map(lambda x: x or '') + expression) | seq(expression, regex(r'[\:\,]') << whitespace.optional(), expression).map(lambda x: "{}: {}".format(x[0], x[2]))
    yield
    
@generate
def argument_list():
    return (literal).sep_by(regex(r',\s*'))
    yield

@generate
def macro_argument_list():
    return whitespace.optional() >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('macro argument name').sep_by(regex(r',\s*')) << whitespace.optional()
    yield
    
@generate
def expr_argument_list():
    return (anonymous_class | arg_expression).sep_by(regex(r',\s*'))
    yield

@generate
def actor_function_call():
    return string('call ').desc("'call' statement").then(regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called function name'))
    yield

@generate
def state_call():
    return seq(
        regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called state function name').skip(whitespace.optional()),
        s('(').then(whitespace.optional()).then(
            expr_argument_list
        ).skip(whitespace.optional()).skip(s(')')).optional()
    )
    yield

@generate
def return_statement():
    return (whitespace.optional() >> s('return')).desc('return statement') # duh
    yield

@generate
def call_literal():
    return seq(
        regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('called expression function name') << whitespace.optional(),
        (s('(') >> whitespace.optional() >>
            expr_argument_list
        << whitespace.optional() << s(')'))
    )
    yield

@generate
def class_body():
    return whitespace.optional().then(
            seq(
                (string("macro ")) >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
                (whitespace.optional() >> s('(') >> whitespace.optional() >> macro_argument_list << whitespace.optional() << s(')') << whitespace.optional()).optional().map(lambda a: a or []).tag('args'),
                state_body.tag('body')
            ).map(dict).tag('macro') |
            seq(
                (string('set') >> whitespace).desc("'set' keyword") >> regex('[a-zA-Z0-9_.]+').tag('name'),
                ((whitespace >> string('to') << whitespace) | (whitespace.optional() >> s('=') << whitespace.optional())).desc("'to' or equal sign") >> literal.sep_by((s(',') + whitespace.optional())).tag('value')
            ).map(dict).tag('property') |
            (((string('is') << whitespace) | string("+")) >> regex('[a-zA-Z0-9_.]+').desc('flag name')).tag('flag') |
            (string('combo') >> whitespace >> regex('[a-zA-Z0-9_.]+').desc('combo name')).tag('flag combo') |
            (((string("isn't") << whitespace) | string('-')) >> regex('[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag') |
            seq((string("function ") | string('method ')) >> regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('function name').tag('name'), state_body.tag('body')).map(dict).tag('function') |
            (seq(((string("label") | string('state')) << whitespace) >> regex('[a-zA-Z_]+').desc('label name').tag('name'), state_body.tag('body')).map(dict) << whitespace.optional()).tag('label')
    ).skip(whitespace.optional()) << s(';') << whitespace.optional()
    yield

@generate
def actor_class():
    return seq(
        (string('actor ') | string('class ')).desc("class statement") >> regex('[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((string(' inherits ') | string(' extends ') | string(' expands ')).desc('inheritance declaration') >> regex('[a-zA-Z0-9_]+')).desc('inherited class name').optional().tag('inheritance').desc('inherited class name'),
        (string(' replaces ') >> regex('[a-zA-Z0-9_]+')).desc('replaced class name').optional().tag('replacement').desc('replacement'),
        (string(' #') >> regex('[0-9]+')).desc('class number').map(int).optional().tag('class number').desc('class number').skip(whitespace.optional()),
        (s('{') >> whitespace.optional() >> class_body.many().optional() << whitespace.optional().then(s('}')).skip(whitespace.optional())).tag('body')
    )
    yield

@generate
def anonymous_class():
    return seq(
        (s('actor') | s('class')).desc("class statement") >> \
                whitespace >> \
                ((string('inherits') | string('extends') | string('expands')).desc('inheritance declaration') >> \
                whitespace >> \
                regex('[a-zA-Z0-9_]+')).desc('inherited class name').optional().tag('inheritance') << \
                whitespace.optional(),

        (
            s('{') >>
            whitespace.optional() >>
            class_body.many().optional() <<
            whitespace.optional() <<
            s('}') <<
            whitespace.optional()
        ).tag('body')
    ).tag('anonymous class')
    yield

@generate
def normal_state():
    return seq(
        regex(r'[A-Z0-9_]{4}').desc('state name').skip(
            whitespace.optional()
        ),
        regex(r"[A-Z_.]").many().desc('state sprite').skip(
            whitespace.optional()
        ),
        regex(r"\-?\d+").map(int).desc('state duration').skip(
            whitespace.optional()
        ),
        modifier.many().desc('modifier').skip(
            whitespace.optional()
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
    return s('{') >> whitespace.optional() >> (state_action << s(';') << whitespace.optional()).many().optional() << s('}')
    yield

@generate
def action_body_repeat():
    return seq(
        s('x') >> whitespace.optional() >> regex(r'\d+').map(int).desc('amount of times to repeat') << whitespace.optional(), state_action
    ).map(lambda x: [x[1] for _ in range(x[0])])
    yield

@generate
def flow_control():
    return (string('stop', transform=lambda s: s.upper()) | string('fail', transform=lambda s: s.upper()) | string('loop', transform=lambda s: s.upper()) | string('goto', transform=lambda s: s.upper()) + whitespace.map(lambda _: ' ') + regex(r'[a-zA-Z0-9\.]+\s?(?:\+\d+)?') | string('wait', transform=lambda s: s.upper()))
    yield

@generate
def macro_call():
    return seq(
        string('inject ').desc("'inject' statement").then(regex('[a-zA-Z_][a-zA-Z_0-9]*').desc('injected macro name')),
        s('(') >> expr_argument_list.desc("macro arguments") << s(')')
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
            whitespace.optional() >> string("{") >> whitespace.optional() >> (
                state | (return_statement << ';').tag('return')
            ).sep_by(whitespace.optional()) << whitespace.optional() << string("}")
        )
    )
    yield

@generate
def sometimes_statement():
    return seq(
        s('sometimes') >>\
                whitespace >>\
                number_lit.tag('chance') <<\
                s('%').optional() <<
                whitespace.optional(),
        state_body.optional().map(lambda x: x if x != None else []).tag('body')
    )
    yield

@generate
def if_statement():
    return seq(
        string("if").desc('if statement')
        .then(whitespace.optional())
        .then(string("("))
        .then(whitespace.optional())
            .then(expression)
        .skip(whitespace.optional())
        .skip(string(")"))
        .skip(whitespace.optional()),
        
        state_body.optional().map(lambda x: x if x != None else [])
        .skip(whitespace.optional()),

        s(';')
        .then(whitespace.optional())
        .then(s('else'))
        .then(whitespace.optional())
            .then(state_body.optional().map(lambda x: x if x != None else []))
        .skip(whitespace.optional())
            .optional()
    )
    yield

@generate
def while_statement():
    return seq(
        string("while").desc('while statement')
            .then(whitespace.optional())
            .then(string("("))
            .then(whitespace.optional())
            .then(expression)
        .skip(whitespace.optional())
        .skip(string(")"))
        .skip(whitespace.optional()),
        state_body.optional().map(lambda x: x if x != None else [])
    )
    yield

@generate
def repeat_statement():
    return seq(
        string('x') >> whitespace.optional() >> regex(r"\d+").map(int).desc('amount of times to repeat'),
        whitespace.optional() >> state_body
    )
    yield

@generate
def source_code():
    return whitespace.optional().desc('ignored whitespace') >> actor_class.sep_by(whitespace.optional()) << whitespace.optional().desc('ignored whitespace')
    yield

def preprocess_code(code, imports=(), defs=(), defines=(), this_fname=None, rel_dir='.'):
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
    begin_char = 0
    
    # comments
    src_lines = code.split('\n')

    code = re.sub(r'\/\/[^\r\n]+', lambda x: re.sub(r'[^\n]', ' ', x.group(0)), code)
    code = re.sub(r'\/\*(\n|.)+?\*\/', lambda x: re.sub(r'[^\n]', ' ', x.group(0)), code)
    codelines = code.split('\n')

    for _i, l in enumerate(codelines):
        i = _i + 1
        src_l = src_lines[_i]

        check_line_case = re.sub(r'^\s+', '', l)
        check_line = check_line_case.upper()

        # preprocessor macro replacement
        for key, value in defines.items():
            l = re.sub(r'\B{}\B'.format(re.escape(key)), value, l)

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
                    lines = preprocess_code(fp.read() + "\n", imports, defs, defines, this_fname=fname, rel_dir=os.path.dirname(fname))

                    for l in lines:
                        pcodelines.append(l)

                    begin_char += lines[-1][4]

            elif check_line.startswith('#DEF ') or check_line.startswith('#DEFINE '):
                key = check_line_case.split(' ')[1]
                value = ' '.join(check_line_case.split(' ')[2:])

                if value != '':
                    defs[key] = None

                else:
                    defs[key] = value

            elif defmacro.match(check_line.split(' ')[0]):
                key = check_line_case.split(' ')[1]
                value = ' '.join(check_line_case.split(' ')[2:])

                if value == '':
                    raise PreprocessingError("Empty macro definitions ('{}') are not allowed!".format(key), i, this_fname, check_line_case)

                defs[key] = value
                defines[key] = value
        
            elif check_line.startswith('#UNDEF ') or check_line.startswith('#UNDEFINE '):
                key = check_line_case.split(' ')[1]

                if key in defs:
                    defs.pop(key)
                    
                if key in defines:
                    defines.pop(key)

        if not check_line.startswith('#') and cond_active:
            pcodelines.append((this_fname, i, src_l, l, begin_char))
            begin_char += len(l) + 1

    return pcodelines

def parse_postcode(postcode, error_handler=None):
    try:
        return (dict(x) for x in source_code.parse('\n'.join(l[3] for l in postcode)))

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
