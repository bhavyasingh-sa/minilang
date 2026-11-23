from automata import compile_regular_expression
from turing import TuringMachine

TOKEN_RULES = [
    ("IF", "if"), ("ELSE", "else"), ("WHILE", "while"), ("PRINT", "print"),
    ("NUMBER", "[0-9]+"), ("IDENT", "[a-zA-Z_][a-zA-Z0-9_]*"),
    ("LE", "<="), ("GE", ">="), ("EQ", "=="), ("NE", "!="), ("LT", "<"), ("GT", ">"),
    ("ASSIGN", "="), ("PLUS", "\\+"), ("MINUS", "-"), ("STAR", "\\*"), ("SLASH", "/"), ("PERCENT", "%"),
    ("LPAREN", "\\("), ("RPAREN", "\\)"), ("LBRACE", "\\{"), ("RBRACE", "\\}"),
    ("NEWLINE", "\n+"), ("SPACE", "[ \t]+"), ("COMMENT", "#[^\n]*"),
]
SKIP = {"SPACE", "COMMENT"}
RULES = [(name, pat, *compile_regular_expression(pat)) for name, pat in TOKEN_RULES]


class LangError(Exception):
    pass


class Token:
    def __init__(self, type, value, line, col):
        self.type, self.value, self.line, self.col = type, value, line, col

    def __repr__(self):
        return f"{self.type}({self.value!r}) @{self.line}:{self.col}"


def tokenize(src):
    tokens, pos, line, col = [], 0, 1, 1
    while pos < len(src):
        best, rule = 0, None
        for name, _, _, _, dfa in RULES:
            n = dfa.longest_match(src, pos)
            if n > best:
                best, rule = n, name
        if rule is None:
            raise LangError(f"unexpected character {src[pos]!r} at line {line}, col {col}")
        text = src[pos:pos + best]
        if rule not in SKIP:
            tokens.append(Token(rule, text, line, col))
        if "\n" in text:
            line, col = line + text.count("\n"), 1
        else:
            col += best
        pos += best
    tokens.append(Token("EOF", "", line, col))
    return tokens


class Node:
    def __init__(self, kind, *kids, **attrs):
        self.kind, self.kids, self.attrs = kind, list(kids), attrs

    def dump(self, depth=0):
        head = "  " * depth + self.kind + ("(" + ", ".join(f"{k}={v!r}" for k, v in self.attrs.items()) + ")" if self.attrs else "")
        return "\n".join([head] + [k.dump(depth + 1) if isinstance(k, Node) else "  " * (depth + 1) + repr(k) for k in self.kids])


BINOPS = {"PLUS": "+", "MINUS": "-", "STAR": "*", "SLASH": "/", "PERCENT": "%",
          "LT": "<", "GT": ">", "LE": "<=", "GE": ">=", "EQ": "==", "NE": "!="}


class Parser:
    def __init__(self, tokens):
        self.toks, self.i = tokens, 0

    @property
    def cur(self):
        return self.toks[self.i]

    def at(self, *types):
        return self.cur.type in types

    def eat(self, type=None):
        t = self.cur
        if type and t.type != type:
            raise LangError(f"expected {type} but found {t.type} ({t.value!r}) at line {t.line}, col {t.col}")
        if t.type != "EOF":
            self.i += 1
        return t

    def program(self):
        stmts = self.stmt_list()
        self.eat("EOF")
        return Node("Program", *stmts)

    def stmt_list(self):
        stmts = []
        while self.at("NEWLINE"):
            self.eat()
        while not self.at("EOF", "RBRACE"):
            stmts.append(self.stmt())
            if not self.at("EOF", "RBRACE"):
                self.eat("NEWLINE")
            while self.at("NEWLINE"):
                self.eat()
        return stmts

    def block(self):
        self.eat("LBRACE")
        stmts = self.stmt_list()
        self.eat("RBRACE")
        return Node("Block", *stmts)

    def stmt(self):
        t = self.cur
        if t.type == "IDENT":
            self.eat()
            self.eat("ASSIGN")
            return Node("Assign", self.expr(), name=t.value, line=t.line)
        if t.type == "PRINT":
            self.eat()
            return Node("Print", self.expr(), line=t.line)
        if t.type == "IF":
            self.eat()
            cond, then = self.expr(), self.block()
            els = Node("Block")
            if self.at("ELSE"):
                self.eat()
                els = self.block()
            return Node("If", cond, then, els, line=t.line)
        if t.type == "WHILE":
            self.eat()
            return Node("While", self.expr(), self.block(), line=t.line)
        raise LangError(f"expected a statement but found {t.type} ({t.value!r}) at line {t.line}, col {t.col}")

    def expr(self):
        left = self.arith()
        if self.at("LT", "GT", "LE", "GE", "EQ", "NE"):
            op = BINOPS[self.eat().type]
            return Node("BinOp", left, self.arith(), op=op)
        return left

    def arith(self):
        node = self.term()
        while self.at("PLUS", "MINUS"):
            op = BINOPS[self.eat().type]
            node = Node("BinOp", node, self.term(), op=op)
        return node

    def term(self):
        node = self.factor()
        while self.at("STAR", "SLASH", "PERCENT"):
            op = BINOPS[self.eat().type]
            node = Node("BinOp", node, self.factor(), op=op)
        return node

    def factor(self):
        t = self.cur
        if t.type == "MINUS":
            self.eat()
            return Node("Neg", self.factor())
        if t.type == "NUMBER":
            self.eat()
            return Node("Num", value=int(t.value))
        if t.type == "IDENT":
            self.eat()
            return Node("Var", name=t.value)
        if t.type == "LPAREN":
            self.eat()
            node = self.expr()
            self.eat("RPAREN")
            return node
        raise LangError(f"expected a number, identifier or '(' but found {t.type} ({t.value!r}) at line {t.line}, col {t.col}")


def parse(src):
    return Parser(tokenize(src)).program()


def tm_add(a, b):
    """This IS the '+' operator (see eval() below) -- every `x + y` in a
    MiniLang program is computed by actually running turing.py's
    binary_addition Turing machine on a and b's binary form and reading the
    sum off its tape when it halts, not by Python's own +. Watch it happen
    for any two numbers with `python3 main.py tm binary_addition <a_bits>+<b_bits>`.
    Falls back to Python's + only when an operand is negative: binary_addition's
    transition table, like a real single-tape adder, has no sign handling."""
    if a < 0 or b < 0:
        return a + b
    if a < b:                      # the machine counts B down to zero, so give it the smaller one
        a, b = b, a
    verdict, _, _, tape = TuringMachine("binary_addition", f"{bin(a)[2:]}+{bin(b)[2:]}").run(show=False)
    if verdict != "ACCEPTED":
        raise LangError(f"addition of {a} and {b} did not finish within the Turing machine step limit")
    return int(tape, 2) if tape else 0


class Interpreter:
    def __init__(self):
        self.env, self.output = {}, []

    def run(self, program):
        for s in program.kids:
            self.exec(s)
        return self.output

    def exec(self, n):
        if n.kind == "Assign":
            self.env[n.attrs["name"]] = self.eval(n.kids[0])
        elif n.kind == "Print":
            v = self.eval(n.kids[0])
            self.output.append(v)
            print(v)
        elif n.kind == "If":
            for s in (n.kids[1] if self.eval(n.kids[0]) else n.kids[2]).kids:
                self.exec(s)
        elif n.kind == "While":
            while self.eval(n.kids[0]):
                for s in n.kids[1].kids:
                    self.exec(s)

    def eval(self, n):
        if n.kind == "Num":
            return n.attrs["value"]
        if n.kind == "Var":
            if n.attrs["name"] not in self.env:
                raise LangError(f"undefined variable '{n.attrs['name']}'")
            return self.env[n.attrs["name"]]
        if n.kind == "Neg":
            return -self.eval(n.kids[0])
        a, b, op = self.eval(n.kids[0]), self.eval(n.kids[1]), n.attrs["op"]
        if b == 0 and op == "/":
            raise LangError("division by zero")
        if b == 0 and op == "%":
            raise LangError("modulo by zero")
        if op == "+":
            return tm_add(a, b)
        if op == "/":
            return (abs(a) // abs(b)) * (1 if (a < 0) == (b < 0) else -1)
        if op == "%":
            return abs(a) % abs(b) * (1 if a >= 0 else -1)
        return {"-": a - b, "*": a * b, "<": int(a < b), ">": int(a > b),
                "<=": int(a <= b), ">=": int(a >= b), "==": int(a == b), "!=": int(a != b)}[op]
