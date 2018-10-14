import string as strlib
import re

from parsy import *


s = string
string_body = regex(r'[^"\\]+')
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
string_delim = s('"') | s("'")
string_literal = string_delim + (string_body | string_esc).many().concat() + string_delim
lwhitespace = whitespace | s('\n') | s('\r')

@generate
def modifier():
    return string('[').then(regex('[a-zA-Z\(\)0-9]+').desc('modifier body')).skip(s(']'))
    yield

def _parse_literal(literal):
    if literal[0] == 'number':
        return str(literal[1])

    elif literal[0] == 'string':
        return literal[1]

    elif literal[0] == 'actor variable':
        return literal[1]

    elif literal[0] == 'call expr':
        return _parse_action(literal[1])

def _parse_action(a):
    print(a)
    return "{}({})".format(a[0], ', '.join(_parse_literal(x) for x in a[1]))

@generate
def literal():
    return (
            string_literal.tag('string') 
        |   call_literal.tag('call expr')
        |   regex(r'[\+\-]?[0-9]+(.[0-9+])?(e[\+\-]?\d+)?').map(float).tag('number')
        |   regex(r'[a-zA-Z_][a-zA-Z0-9_\[\]]*').tag('actor variable')
        |   regex(r'0x[0-9A-Fa-f]+').map(float).tag('number')
        |   regex(r'0b[01]+').map(float).tag('number')
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
                    literal.map(_parse_literal)
                |   regex(r'[\+\-\|\>\<\~\&\!\=\*\/\%]+')
                |   paren_expr
            ).sep_by(whitespace.optional()).map(lambda x: ' '.join(x))
        )
        << whitespace.optional()
    )
    yield
    
@generate
def argument_list():
    return literal.sep_by(regex(',\s*'))
    yield

@generate
def actor_function_call():
    return string('call ').desc("'calls' statement").then(regex('[a-zA-Z_]+').desc('called function name'))
    yield

@generate
def state_call():
    return seq(
        regex('[a-zA-Z_]+').desc('called state function name').skip(whitespace.optional()),
        s('(').then(whitespace.optional()).then(
            argument_list
        ).skip(whitespace.optional()).skip(s(')')).optional()
    )
    yield

@generate
def call_literal():
    return seq(
        regex('[a-zA-Z_]+').desc('called state function name').skip(whitespace.optional()),
        s('(').then(whitespace.optional()).then(
            argument_list
        ).skip(whitespace.optional()).skip(s(')'))
    )
    yield

@generate
def class_body():
    return whitespace.optional().then(
                seq(
                    (string('set') >> whitespace).desc("'set' keyword") >> regex('[a-zA-Z0-9_.]+').tag('name'),
                    ((whitespace >> string('to') << whitespace) | (whitespace.optional() >> s('=') << whitespace.optional())).desc("'to' or equal sign") >> literal.tag('value')
                ).map(dict).tag('property')
            |   (((string('is') << whitespace) | string("+")) >> regex('[a-zA-Z0-9_.]+').desc('flag name')).tag('flag')
            |   (((string("isn't") << whitespace) | string('-')) >> regex('[a-zA-Z0-9_\.]+').desc('flag name')).tag('unflag')
            |   seq((string("function ") | string('method ')) >> regex('[a-zA-Z_]+').desc('function name').tag('name'), state_body.tag('body')).map(dict).tag('function')
            |   (seq(((string("label") | string('state')) << whitespace) >> regex('[a-zA-Z_]+').desc('label name').tag('name'), state_body.tag('body')).map(dict) << whitespace.optional()).tag('label')
    ).skip(whitespace.optional()) << s(';') << whitespace.optional()
    yield

@generate
def actor_class():
    return seq(
        (string('actor ') | string('class ')).desc("class statement") >> regex('[a-zA-Z0-9_]+').desc('class name').tag('classname'),
        ((string(' inherits ') | string(' extends ') | string(' expands ')) >> regex('[a-zA-Z0-9_]+')).desc('inherited class name').optional().tag('inheritance'),
        (string(' replaces ') >> regex('[a-zA-Z0-9_]+')).desc('replaced class name').optional().tag('replacement'),
        (string(' #') >> regex('[0-9]+')).desc('class number').map(int).optional().tag('class number').skip(whitespace.optional()),
        (s('{') >> whitespace.optional() >> class_body.many().optional() << whitespace.optional().then(s('}')).skip(whitespace.optional())).tag('body')
    )
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
        regex(r"\d+").map(int).desc('state duration').skip(
            whitespace.optional()
        ),
        modifier.many().desc('modifier').skip(
            whitespace.optional()
        ).optional(),
        state_call.optional()
    )
    yield

@generate
def flow_control():
    return (string('stop') | string('fail') | string('loop') | string('goto') + whitespace.map(lambda _: ' ') + regex(r'[a-zA-Z]+\s?(?:\+\d+)?') | string('wait'))
    yield

@generate
def state():
    return (if_statement.tag('if') | while_statement.tag('while') | actor_function_call.tag('call') | flow_control.tag('flow') | normal_state.tag('frames') | repeat_statement.tag('repeat')).skip(s(';'))
    yield

@generate
def state_no_colon():
    return (if_statement.tag('if') | while_statement.tag('while') | actor_function_call.tag('call') | flow_control.tag('flow') | normal_state.tag('frames') | repeat_statement.tag('repeat'))
    yield

@generate
def state_body():
    return (state_no_colon.map(lambda x: [x]) | whitespace.optional() >> string("{") >> whitespace.optional() >> state.sep_by(whitespace.optional()) << whitespace.optional() << string("}"))
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
        state_body
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
        state_body
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

def parse_code(code):
    rcode = code

    for l in rcode.split('\n'):
        if l.startswith('#IMPORT ') or l.startswith('#INCLUDE '):
            fname = l.split(' ')[1]

            with open(fname) as fp:
                code.replace(l, fp.read() + "\n")

        elif len(set(l) - set(strlib.whitespace + '#')) > 0:
            break

    code = re.sub(r'\/\/[^\r\n]+', lambda x: ' ' * len(x.group(0)), code)
    code = re.sub(r'\/\*.+?\*\/', lambda x: ' ' * len(x.group(0)), code)

    return (dict(x) for x in source_code.parse(code))