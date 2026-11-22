EPS = None
ALPHABET = frozenset(chr(c) for c in range(32, 127)) | frozenset("\t\n")
ESCAPES = {"n": "\n", "t": "\t", "r": "\r"}
CLASS_ESCAPES = {
    "d": frozenset("0123456789"),
    "w": frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"),
    "s": frozenset(" \t\n\r"),
}


class RegularExpressionParser:
    def __init__(self, s):
        self.s, self.i = s, 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def next(self):
        self.i += 1
        return self.s[self.i - 1]

    def parse(self):
        node = self.expr()
        if self.i != len(self.s):
            raise ValueError(f"bad regular expression /{self.s}/ at {self.i}")
        return node

    def expr(self):
        alts = [self.term()]
        while self.peek() == "|":
            self.next()
            alts.append(self.term())
        return alts[0] if len(alts) == 1 else ("union", alts)

    def term(self):
        parts = []
        while self.peek() is not None and self.peek() not in "|)":
            parts.append(self.factor())
        if not parts:
            return ("eps",)
        return parts[0] if len(parts) == 1 else ("concat", parts)

    def factor(self):
        node = self.base()
        while self.peek() in ("*", "+", "?"):
            node = ({"*": "star", "+": "plus", "?": "opt"}[self.next()], node)
        return node

    def base(self):
        ch = self.peek()
        if ch is None:
            raise ValueError(f"unexpected end of /{self.s}/")
        if ch == "(":
            self.next()
            node = self.expr()
            if self.next() != ")":
                raise ValueError(f"unclosed ( in /{self.s}/")
            return node
        if ch == "[":
            return self.charclass()
        self.next()
        if ch == "\\":
            esc = self.next()
            if esc in CLASS_ESCAPES:
                return ("set", CLASS_ESCAPES[esc])
            ch = ESCAPES.get(esc, esc)
        elif ch in "*+?)|]":
            raise ValueError(f"unescaped {ch!r} in /{self.s}/")
        return ("set", frozenset([ch]))

    def charclass(self):
        self.next()
        negate = self.peek() == "^"
        if negate:
            self.next()
        chars = set()
        while self.peek() != "]":
            if self.peek() is None:
                raise ValueError(f"unclosed [ in /{self.s}/")
            lo = self.next()
            if lo == "\\":
                esc = self.next()
                if esc in CLASS_ESCAPES:
                    chars.update(CLASS_ESCAPES[esc])
                    continue
                lo = ESCAPES.get(esc, esc)
            if self.peek() == "-" and self.i + 1 < len(self.s) and self.s[self.i + 1] != "]":
                self.next()
                hi = self.next()
                chars.update(chr(c) for c in range(ord(lo), ord(hi) + 1))
            else:
                chars.add(lo)
        self.next()
        return ("set", frozenset(ALPHABET - chars if negate else chars))


class NFA:
    def __init__(self):
        self.trans, self.start, self.accept, self.n = {}, 0, set(), 0

    def state(self):
        self.trans[self.n] = {}
        self.n += 1
        return self.n - 1

    def edge(self, a, sym, b):
        self.trans[a].setdefault(sym, set()).add(b)

    def alphabet(self):
        return {s for e in self.trans.values() for s in e if s is not EPS}

    def closure(self, states):
        seen, stack = set(states), list(states)
        while stack:
            for t in self.trans[stack.pop()].get(EPS, ()):
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
        return frozenset(seen)

    def move(self, states, sym):
        return self.closure({t for s in states for t in self.trans[s].get(sym, ())})

    def run(self, text):
        cur = self.closure({self.start})
        for ch in text:
            cur = self.move(cur, ch)
        return bool(cur & self.accept)


def thompson(nfa, node):
    kind = node[0]
    s, e = nfa.state(), nfa.state()
    if kind == "set":
        for ch in node[1]:
            nfa.edge(s, ch, e)
    elif kind == "eps":
        nfa.edge(s, EPS, e)
    elif kind == "concat":
        prev = s
        for part in node[1]:
            ps, pe = thompson(nfa, part)
            nfa.edge(prev, EPS, ps)
            prev = pe
        nfa.edge(prev, EPS, e)
    elif kind == "union":
        for alt in node[1]:
            a_s, a_e = thompson(nfa, alt)
            nfa.edge(s, EPS, a_s)
            nfa.edge(a_e, EPS, e)
    else:
        c_s, c_e = thompson(nfa, node[1])
        nfa.edge(s, EPS, c_s)
        nfa.edge(c_e, EPS, e)
        if kind in ("star", "plus"):
            nfa.edge(c_e, EPS, c_s)
        if kind in ("star", "opt"):
            nfa.edge(s, EPS, e)
    return s, e


def regular_expression_to_nfa(pattern):
    nfa = NFA()
    nfa.start, end = thompson(nfa, RegularExpressionParser(pattern).parse())
    nfa.accept = {end}
    return nfa


class DFA:
    def __init__(self):
        self.trans, self.start, self.accept, self.alphabet = {}, 0, set(), set()

    @property
    def n(self):
        return len(self.trans)

    def run(self, text):
        s = self.start
        for ch in text:
            if ch not in self.trans[s]:
                return False
            s = self.trans[s][ch]
        return s in self.accept

    def longest_match(self, text, pos):
        s, best, i = self.start, 0, pos
        while i < len(text) and text[i] in self.trans[s]:
            s = self.trans[s][text[i]]
            i += 1
            if s in self.accept:
                best = i - pos
        return best

    def table(self):
        return [(a, sym, b) for a in sorted(self.trans) for sym, b in sorted(self.trans[a].items())]

    def to_dot(self, name="G"):
        out = [f"digraph {name} {{ rankdir=LR; node [shape=circle];"]
        out += [f"  {s} [shape=doublecircle];" for s in self.accept]
        out.append(f"  _ [shape=point]; _ -> {self.start};")
        out += [f'  {a} -> {b} [label="{sym!r}"];' for a, sym, b in self.table()]
        return "\n".join(out) + "\n}"


def subset_construction(nfa):
    dfa = DFA()
    dfa.alphabet = nfa.alphabet()
    start = nfa.closure({nfa.start})
    ids, work = {start: 0}, [start]
    dfa.trans[0] = {}
    while work:
        subset = work.pop()
        if subset & nfa.accept:
            dfa.accept.add(ids[subset])
        for sym in dfa.alphabet:
            dest = nfa.move(subset, sym)
            if not dest:
                continue
            if dest not in ids:
                ids[dest] = len(ids)
                dfa.trans[ids[dest]] = {}
                work.append(dest)
            dfa.trans[ids[subset]][sym] = ids[dest]
    return dfa


def minimize(dfa):
    DEAD = -1
    states = list(dfa.trans) + [DEAD]
    group = {s: int(s in dfa.accept) for s in states}
    while True:
        sig = {s: (group[s], tuple(group[dfa.trans.get(s, {}).get(a, DEAD)] for a in sorted(dfa.alphabet))) for s in states}
        ids = {}
        new = {s: ids.setdefault(sig[s], len(ids)) for s in states}
        if len(set(new.values())) == len(set(group.values())):
            break
        group = new
    dead = group[DEAD]
    live = sorted(set(group.values()) - {dead})
    remap = {g: i for i, g in enumerate(live)}
    m = DFA()
    m.alphabet = dfa.alphabet
    m.trans = {i: {} for i in remap.values()}
    for s in dfa.trans:
        if group[s] != dead:
            for a, t in dfa.trans[s].items():
                if group[t] != dead:
                    m.trans[remap[group[s]]][a] = remap[group[t]]
    m.start = remap[group[dfa.start]]
    m.accept = {remap[group[s]] for s in dfa.accept}
    return m


def compile_regular_expression(pattern):
    nfa = regular_expression_to_nfa(pattern)
    dfa = subset_construction(nfa)
    return nfa, dfa, minimize(dfa)
