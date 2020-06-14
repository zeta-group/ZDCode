# pylint: disable=unreachable
import re
import sys
import os
import glob
import traceback
import parsy

try:
    import simplejson as json

except ImportError:
    import json

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
def state_modifier_name():
    return (s('{') >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('modifier parameter name').tag('replace') << s('}') | regex(r'[a-zA-Z\(\)0-9\'\",\w"]').tag('char')).many().desc('modifier body')
    yield

@generate
def modifier():
    # State modifier. Not to be confused with the 'mod' modifier block.
    return string('[').then(state_modifier_name).skip(s(']'))
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
def group_name():
    return regex(r'[a-zA-Z0-9_]+').desc('group name')
    yield
    
@generate
def p_group_name():
    return regex(r'\@*[a-zA-Z0-9_]+').desc('group name')
    yield

@generate
def variable_name():
    return regex(r'[a-zA-Z_\$][a-zA-Z0-9_\$\[\]]*')
    yield

@generate
def literal():
    return (
        call_literal.tag('call expr').desc('call') |
        string_literal.tag('string').desc('string') |
        variable_name.tag('actor variable').desc('actor variable') |
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
    return parameter.tag('position arg').desc('positional argument value')
    yield

@generate
def argument_list():
    return (literal).sep_by(regex(r',\s*'))
    yield

@generate
def macro_argument_list():
    return wo >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('macro argument name').sep_by(regex(r',\s*')) << wo
    yield

@generate
def template_parameter_list():
    return wo >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('template parameter name').sep_by(regex(r',\s*')) << wo
    yield

@generate
def expr_argument_list():
    return arg_expression.sep_by(s(',') >> wo)
    yield

@generate
def parameter():
    return anonymous_class | anonymous_macro | templated_class_derivation | expression.tag('expression')
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
    return ist('call ').desc("'call' statement").then(regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('called function name'))
    yield

@generate
def state_call():
    return seq(
        regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('called state function name').skip(wo),
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
def continue_statement():
    return (wo >> ist('continue')).desc('continue statement')
    yield
    
@generate
def break_statement():
    return (wo >> ist('break')).desc('break statement')
    yield

@generate
def call_literal():
    return seq(
        regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('called expression function name') << wo,
        (s('(') >> wo >>
            expr_argument_list
        << wo << s(')'))
    )
    yield

@generate
def label():
    return (seq(((ist("label") | ist('state')) << whitespace) >> regex(r'[a-zA-Z_]+').desc('label name').tag('name'), state_body.tag('body')).map(dict) << wo)
    yield

@generate
def templated_class_derivation():
    return seq(
        regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('name of templated class').skip(wo),
        (s('::(').then(wo).then(
            parameter_list.optional().map(lambda x: x if x and tuple(x) != ('',) else [])
        ).skip(wo).skip(s(')'))),
        (
            wo.then(s('{')).then(
                wo.then(
                    (((ist('is') << whitespace) | string("+")) >> regex(r'[a-zA-Z0-9_\.]+').desc('flag name')).tag('flag') |
                    (((ist("isn't") << whitespace) | string('-')) >> regex(r'[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag') |

                    ist("macro").then(whitespace).then(seq(
                        regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
                        (wo >> s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []).tag('args'),
                        state_body.tag('body')
                    ).map(dict).desc('override macro').tag('macro')) |
                    
                    seq(
                        (ist('set') >> whitespace).desc("'set' keyword") >> regex(r'[a-zA-Z0-9_\.]+').tag('name'),
                        ((whitespace >> ist('to') << whitespace) | (wo >> s('=') << wo)).desc("'to' or equal sign") >> parameter.sep_by((s(',') << wo)).tag('value')
                    ).map(dict).tag('property') |

                    label.desc('override label').tag('label') |

                    ((ist('var') << whitespace) >> seq(
                        regex(r'user_[a-zA-Z0-9_]+').desc('var name').tag('name'),
                        (wo.then(s('[')).then(replaceable_number).skip(s(']'))).optional().map(lambda x: int(x or 0)).tag('size'),
                        (wo.then(s(':')).then(wo).then(regex(r'[a-zA-Z_.][a-zA-Z0-9_]+'))).desc('var type').optional().map(lambda t: t or 'int').tag('type'),
                        (wo.then(s('=')).then(expression.tag('val') | array_literal.tag('arr'))).optional().tag('value')
                    ).map(dict).tag('user var')) |

                    ((ist('array') << whitespace) >> seq(
                        regex(r'user_[a-zA-Z0-9_]+').desc('array name').tag('name'),
                        (wo >> s('=') >> wo >> array_literal).desc('array values').tag('value')
                    ).map(dict).desc('override array').tag('array'))
                ).skip(wo).skip(s(';')).skip(wo).many().optional()
            ).skip(s('}'))
        ).optional().map(lambda x: x or [])
    ).tag('template derivation').desc('template derivation')
    yield

@generate
def static_template_derivation():
    return wo >> seq(
        ist('derive') >> whitespace >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('name of derived class').tag('classname'),
        ((ist('group') << whitespace).desc('group keyword') >> group_name).optional().map(lambda x: x or None).tag('group'),
        whitespace >> ist('as') >> whitespace >> templated_class_derivation.tag('source'),
        
    ).desc('static template derivation') << s(';') << wo
    yield

@generate
def mod_name():
    return regex(r'[a-zA-Z_-][a-zA-Z_0-9-]+')
    yield

@generate
def mod_block():
    return (seq((ist("mod") << whitespace) >> mod_name.desc('modifier name'), mod_block_body) << wo)
    yield

@generate
def class_body():
    return wo.then(
            seq(
                ist("macro") >> whitespace >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
                (wo >> s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []).tag('args'),
                state_body.tag('body')
            ).map(dict).tag('macro') |
            seq(
                (ist('set') >> whitespace).desc("'set' keyword") >> regex(r'[a-zA-Z0-9_\.]+').tag('name'),
                ((whitespace >> ist('to') << whitespace) | (wo >> s('=') << wo)).desc("'to' or equal sign") >> parameter.sep_by((s(',') << wo)).tag('value')
            ).map(dict).tag('property') |
            (((ist('is') << whitespace) | string("+")) >> regex(r'[a-zA-Z0-9_\.]+').desc('flag name')).tag('flag') |
            (ist('var') << whitespace) >> seq(
                regex(r'user_[a-zA-Z0-9_]+').desc('var name').tag('name'),
                (wo >> s('[') >> replaceable_number << s(']')).desc('array size').optional().map(lambda x: int(x or 0)).tag('size'),
                (wo >> s(':') >> wo >> regex(r'[a-zA-Z_.][a-zA-Z0-9_]+')).desc('var type').optional().map(lambda t: t or 'int').tag('type'),
                (wo >> s('=') >> (expression.tag('val') | array_literal.tag('arr'))).optional().tag('value')
            ).map(dict).tag('user var') |
            (((ist("isn't") << whitespace) | string('-')) >> regex(r'[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag') |
            (ist('combo') >> whitespace >> regex(r'[a-zA-Z0-9_]+').desc('combo name')).tag('flag combo') |
            seq((ist("function ") | ist('method ')) >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('function name').tag('name'), state_body.tag('body')).map(dict).tag('function') |
            label.tag('label') |
            mod_block.tag('mod')
    ).skip(wo) << s(';') << wo
    yield

@generate
def abstract_label_body():
    return (ist("abstract label") | ist('abstract state')) >> whitespace >> regex(r'[a-zA-Z_]+').desc('label name') << s(';')
    yield

@generate
def abstract_array_body():
    return seq(
        ist("abstract array") >> whitespace >> regex(r'user_[a-zA-Z0-9_]+').desc('array name').tag('name'),
        (wo >> s('[') >> replaceable_number << s(']')).optional().map(lambda x: int(x) if x else 'any').tag('size'),
        (wo >> s(':') >> wo >> regex(r'[a-zA-Z_.][a-zA-Z0-9_]+')).desc('var type').optional().map(lambda t: t or 'int').tag('type')
    ).map(dict) << wo << s(';') << wo
    yield

@generate
def abstract_macro_body():
    return seq(
        ist("abstract macro") >> whitespace >> regex(r'[a-zA-Z_]+').desc('macro name').tag('name') << wo,
        (s('(') >> wo >> macro_argument_list << wo << s(')')).optional().map(lambda x: x or []).tag('args')
    ).map(dict) << wo << s(';') << wo
    yield

@generate
def sprite_name():
    return (
        (regex(r'[A-Z0-9_]{4}') | s('"#"')).tag('normal') |
        (ist('param') >> whitespace >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*')).tag('parametrized')
    )
    yield

@generate
def superclass():
    return (
        templated_class_derivation |
        regex(r'[a-zA-Z][a-zA-Z0-9_]+').tag('classname')
    )
    yield

@generate
def group_declaration():
    return seq(
        ((ist('group') << whitespace).desc('group statement') >> wo >> group_name).tag('name'),
        (wo >> s('{') >> regex(r'[a-zA-Z0-9_]+').sep_by(s(',') << wo) << s('}')).optional().map(lambda x: x if x and tuple(x) != ('',) else []).tag('items')
    ) << s(';')
    yield

@generate
def actor_class():
    return seq(
        ((ist('actor') | ist('class')) << whitespace).desc("class statement") >> regex(r'[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((whitespace >> ist('group') << whitespace).desc('group keyword') >> group_name).optional().map(lambda x: x or None).tag('group'),
        ((whitespace >> (ist('inherits') | ist('extends') | ist('expands'))) >> whitespace >> superclass.desc('inherited class')).optional().tag('inheritance').desc('inherited class name'),
        (whitespace >> (ist('replaces') >> whitespace >> regex(r'[a-zA-Z0-9_]+'))).desc('replaced class name').optional().tag('replacement').desc('replacement'),
        (whitespace >> s('#') >> regex(r'[0-9]+')).desc('class number').map(int).optional().tag('class number').desc('class number').skip(wo),

        (s('{') >> wo >> class_body.many().optional() << wo.then(s('}')).skip(wo)).tag('body')
    )
    yield

@generate
def templated_actor_class():
    return seq(
        (ist('actor') | ist('class') | ist('template')).desc("class template") >> s('<') >> template_parameter_list.tag('parameters') << s('>') << wo,
        regex(r'[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((whitespace >> ist('group') << whitespace).desc('group keyword') >> group_name).optional().map(lambda x: x or None).tag('group'),
        ((whitespace >> (ist('inherits') | ist('extends') | ist('expands'))) >> whitespace >> superclass.desc('inherited class')).optional().tag('inheritance').desc('inherited class name'),
        (whitespace >> (ist('replaces') >> whitespace >> regex(r'[a-zA-Z0-9_]+'))).desc('replaced class name').optional().tag('replacement').desc('replacement'),
        (whitespace >> s('#') >> regex(r'[0-9]+')).desc('class number').map(int).optional().tag('class number').desc('class number').skip(wo),

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
                
        ((ist('group') << whitespace).desc('group keyword') >> group_name).optional().map(lambda x: x or None).tag('group'),

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
        ist('keepst').desc('\'keepst\' state').skip(whitespace) >>\
        regex(r"\-?\d+").map(int).desc('state duration').skip(wo),
        modifier.many().desc('modifier').skip(wo).optional(),
        state_action.optional()
    ).map(lambda l: [('normal', '"####"'), '"#"', *l]) | seq(
        ist('invisi').desc('\'invisi\' state').skip(whitespace) >>\
        regex(r"\-?\d+").map(int).desc('state duration').optional().map(lambda x: x or 0).skip(wo),
        modifier.many().desc('modifier').skip(wo).optional(),
        state_action.optional()
    ).map(lambda l: [('normal', 'TNT1'), 'A', *l])
    yield

@generate
def state_action():
    return action_body_repeat.tag('repeated inline body') | state_call.tag('action') | action_body.tag('inline body')
    yield

@generate
def action_body():
    return s('{') >> wo >> (state_action << s(';') << wo).many().optional() << s('}')
    yield

@generate
def replaceable_number():
    return (
        regex(r'\d+').map(int) |
        variable_name
    )
    yield

@generate
def action_body_repeat():
    return seq(
        ist('x') >> wo >> replaceable_number.desc('amount of times to repeat'),
        (whitespace >> ist('index') >> whitespace >> variable_name.desc('repeat index name') << whitespace).optional().map(lambda x: x or None),
        wo >> state_action
    )
    yield

@generate
def flow_control():
    return (ist('stop') | ist('wait') | ist('fail') | ist('loop') | ist('goto') + whitespace.map(lambda _: ' ') + regex(r'[a-zA-Z0-9\:\.]+\s?(?:\+\d+)?'))
    yield

@generate
def macro_call():
    return seq(
        ( ist('from').desc("'from' determiner").then(whitespace).then(regex(r'\@*[a-zA-Z_][a-zA-Z_0-9]*').desc('extern macro classname')).skip(whitespace) ).optional().map(lambda x: x or None),
        ist('inject').desc("'inject' statement").then(whitespace).then(regex(r'\@*[a-zA-Z_][a-zA-Z_0-9]*').desc('injected macro name')).skip(wo),
        (s('(') >> expr_argument_list.desc("macro arguments") << s(')')).optional().map(lambda x: x or [])
    )
    yield

@generate
def state():
    return state_no_colon << s(';')
    yield

@generate
def state_no_colon():
    return (
        return_statement.tag('return') |
        break_statement.tag('break') |
        continue_statement.tag('continue') |
        if_statement.tag('if') |
        ifjump_statement.tag('ifjump') |
        whilejump_statement.tag('whilejump') |
        for_statement.tag('for') |
        sometimes_statement.tag('sometimes') |
        while_statement.tag('while') |
        actor_function_call.tag('call') |
        apply_block.tag('apply') |
        macro_call.tag('inject') |
        flow_control.tag('flow') |
        normal_state.tag('frames') |
        repeat_statement.tag('repeat')
    )
    yield

# Modifier effect functions.
def mod_flag(mod):
    def _eff(code, ctx, state):
        state.keywords.append(code._parse_state_modifier(mod))
        yield
    return _eff

def mod_prefix(pre):
    def _eff(code, ctx, state):
        yield from code._parse_state_expr(ctx, state)
        yield state
    return _eff

def mod_suffix(pre):
    def _eff(code, ctx, state):
        yield state
        yield from code._parse_state_expr(ctx, state)
    return _eff

def mod_manipulate(state_macro_name, state_body):
    def _eff(code, ctx, state):
        fake_macro = [state]
        
        new_ctx = ctx.derive('effect manipulation')
        new_ctx.macros[state_macro_name.upper()] = fake_macro
        
        yield from code._parse_state_expr(new_ctx, state_body)
    return _eff

@generate
def modifier_effect():
    # A modifier effect.
    return (
        (ist('flag') >> wo >> state_modifier_name).map(mod_flag),
        (ist('prefix') >> wo >> state_body).map(mod_prefix),
        (ist('suffix') >> wo >> state_body).map(mod_suffix),
        (ist('manipulate') >> wo >> seq(
            regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('virtual macro name') << wo,
            state_body.desc('manipulated state body template')
        )).tag('manipulate'),
    )
    yield
    
@generate
def modifier_effect_body():
    # A modifier effect with semicolon.
    return (
        modifier_effect << wo << s(';') << wo
    )
    yield

@generate
def modifier_selector_basic():
    # A basic state selector, the building blocks of a
    # state selector in a modifier

    return (
        ist('all') .result(lambda _: True),
        ist('none').result(lambda _: False),
        
        (
            (ist('flag') >> wo >> s('(') >> state_modifier_name << s(')'))
                .map(lambda name: (
                    lambda code, ctx, state: state.keywords and code._parse_state_modifier(ctx, name) in state.keywords
                ))
        ).desc('flag selector'),

        (
            (ist('sprite') >> wo >> s('(') >> sprite_name << s(')'))
                .map(lambda name: (
                    lambda code, ctx, state: code._parse_state_sprite(ctx, name) == state.sprite
                ))
        ).desc('sprite selector'),
    )
    yield

@generate
def modifier_selector_expr():
    # A selector is an expression, always enclosed between
    # parens, where basic selectors are joined by boolean
    # logic.

    return wo >> s('(') >> wo >> (
        modifier_selector_basic | (
            (s('(') >> modifier_selector_expr << s(')')) |
            (s('!') >> wo >> modifier_selector_expr).map(lambda a: (lambda code, ctx, state: not a(code, ctx, state))) |
            (seq(modifier_selector_expr, wo >> s('&&') >> wo >> modifier_selector_expr)).map(lambda a: (lambda code, ctx, state: a[0](code, ctx, state) and a[1](code, ctx, state))) |
            (seq(modifier_selector_expr, wo >> s('||') >> wo >> modifier_selector_expr)).map(lambda a: (lambda code, ctx, state: a[0](code, ctx, state)  or a[1](code, ctx, state))) |
            (seq(modifier_selector_expr, wo >> s('^^') >> wo >> modifier_selector_expr)).map(lambda a: (lambda code, ctx, state: a[0](code, ctx, state)  != a[1](code, ctx, state)))
        )
    ) << wo << s(')') << wo
    yield

@generate
def modifier_clause():
    # One clause, a selector and its respective effects.
    return seq(
        modifier_selector_expr.desc('modifier selector expression'),
        (
            modifier_effect_body.map(lambda e: [e]) |
            (wo >> s('{') >> wo >> modifier_effect_body.many() << wo << s('}') << wo << s(';'))
        ).desc('modifier effects body')
    )
    yield

@generate
def mod_block_body():
    return modifier_clause.map(lambda a: [a]) | (
        wo >> s('{') >> wo >> (
            (modifier_clause << wo << s(';')).many()
        ) << wo << s('}') << wo << s(';')
    )
    yield

@generate
def state_body():
    return (
        state_no_colon.map(lambda x: [x]) | (
            wo >> string("{") >> wo >> (state).sep_by(wo) << wo << string("}")
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
def apply_block():
    return seq(
        ist('apply').desc('apply statement')
        .then(whitespace)
            .then(mod_name)
        .skip(wo),

        state_body.desc('apply block body')
        .skip(wo)
    )

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
def for_statement():
    return seq(
        ist("for").desc('for statement')
        .then(whitespace)
        .then(variable_name.desc('iteration parameter name'))
        .skip(whitespace),
        
        (
            ist('index').desc('index keyword')
            .then(whitespace)
            .then(variable_name.desc('iteration index name'))
            .skip(whitespace)
        ).optional().map(lambda x: x or None),

        # state_body.optional().map(lambda x: x if x != None else [])
        ist("in")
        .then(whitespace)
        .then((
            # Possible iteration modes
            (ist("group") >> whitespace >> p_group_name << whitespace).tag('group')
        ))
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
def ifjump_statement():
    return seq(
        ist("ifjump").desc('ifjump statement')
        .then(whitespace)
        .then(state_call)
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
def whilejump_statement():
    return seq(
        ist("whilejump").desc('whilejump statement')
        .then(whitespace)
        .then(state_call)
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
def repeat_statement():
    return seq(
        ist('x') >> wo >> replaceable_number.desc('amount of times to repeat'),
        (whitespace >> ist('index') >> whitespace >> variable_name.desc('repeat index name') << whitespace).optional().map(lambda x: x or None),
        wo >> state_body
    )
    yield

@generate
def anonymous_macro():
    return seq(
        ist("macro") >> (s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []),
        state_body
    ).tag('anonymous macro')
    yield

@generate
def macro_def():
    return seq(
        ist("macro") >> whitespace >> regex(r'[a-zA-Z_][a-zA-Z_0-9]*').desc('macro name').tag('name'),
        (wo >> s('(') >> macro_argument_list << s(')') << wo).optional().map(lambda a: a or []).tag('args'),
        state_body.tag('body')
    ).map(dict).tag('macro')
    yield

@generate
def source_code():
    return wo.desc('ignored whitespace') >> (group_declaration.tag('group') | macro_def.tag('macro') | actor_class.tag('class') | static_template_derivation.tag('static template derivation') | templated_actor_class.tag('class template')).sep_by(wo) << wo.desc('ignored whitespace')
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

                raise PreprocessingError("Unexpected parse error using parametrized preprocessor alias '{}' ({})".format(key, e), i, this_fname, code + '\n\n')

            if len(d_args) != len(args):
                raise PreprocessingError("Bad number of arguments using parametrized preprocessor alias '{}': expected {}, got {}!".format(key, len(d_args), len(args)), i, this_fname, code)

            v = val

            for aname, aval in zip(d_args, args):
                #ov = v
                v = re.sub(r'\({}\)'.format(re.escape(aname)), '({})'.format(aval), v)

            res = preprocess_for_macros(v, defines, this_fname, i)
            nl += res

        l = nl

    return l

def preprocess_code(code, imports=(), defs=(), defines=(), this_fname=None, rel_dir='.', begin_char=None):
    if not begin_char:
        begin_char = [0]

    if not isinstance(imports, dict):
        imports = dict(imports)

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
                gfname = os.path.join(rel_dir, ' '.join(check_line_case.split(' ')[1:]))
                gname = glob.glob(gfname)
                
                if gname:
                    for fname in gname:
                        if not os.path.isfile(fname):
                            raise PreprocessingError("The module '{}' was not found".format(fname), i, this_fname, check_line_case)

                        if imports.get(fname, object()) == this_fname:
                            raise PreprocessingError("The module '{}' was found in an infinite import cycle!".format(fname), i, this_fname, check_line_case)

                        elif fname not in imports:
                            imports[fname] = this_fname

                            with open(fname) as fp:
                                lines = preprocess_code(fp.read() + "\n", imports, defs, defines, this_fname=fname, rel_dir=os.path.dirname(fname), begin_char=begin_char)

                                for l in lines:
                                    pcodelines.append(l)
                            
                else:
                    raise PreprocessingError("No module matching '{}' was found".format(gfname), i, this_fname, check_line_case)
                        
            elif check_line.startswith('#RESOURCE ') or check_line.startswith('#RES '):
                # Add resource to output PK3
                key = check_line_case.split(' ')[1]
                value = ' '.join(check_line_case.split(' ')[2:])

                if value == '':
                    defs[key] = None

                else:
                    defs[key] = value

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

def parse_code(code, filename=None, dirname='.', error_handler=None, imports=()):
    try:
        return parse_postcode(preprocess_code(code, this_fname=filename, rel_dir=dirname, imports=imports), error_handler=error_handler)

    except PreprocessingError as pperr:
        if error_handler is None:
            raise

        else:
            error_handler(pperr)
