import sys
from automata import compile_regular_expression
from lang import TOKEN_RULES, RULES, LangError, tokenize, parse, Interpreter
from turing import MACHINES, TuringMachine

USAGE = """usage:
  python3 main.py run [--verbose] FILE.ml      run a MiniLang program
  python3 main.py repl                         interactive read-eval-print loop
  python3 main.py show TOKEN [--dot]           NFA/DFA/minimal DFA for one token rule
  python3 main.py regular-expression PATTERN STRING...   compile a regular expression and test strings
  python3 main.py tm MACHINE INPUT [--quiet]   run a Turing machine
machines: """ + ", ".join(MACHINES) + "\ntokens:   " + ", ".join(n for n, _ in TOKEN_RULES)


def esc(p):
    return p.replace("\n", "\\n").replace("\t", "\\t")


def print_dfa(title, dfa):
    print(f"  {title}: {dfa.n} states, start={dfa.start}, accept={sorted(dfa.accept)}")
    for a, sym, b in dfa.table():
        print(f"    {a:>3} --{sym!r}--> {b}")


def cmd_run(args):
    verbose = "--verbose" in args
    src = open([a for a in args if not a.startswith("--")][0]).read()
    if verbose:
        print("=== tokens ===")
        for t in tokenize(src):
            print(" ", t)
        print("\n=== token rules: NFA -> DFA -> minimal DFA (states) ===")
        for name, pat, nfa, dfa, mdfa in RULES:
            print(f"  {name:<8} /{esc(pat):<22}/ {nfa.n:>3} -> {dfa.n:>3} -> {mdfa.n:>3}")
        print("\n=== parse tree ===")
    program = parse(src)
    if verbose:
        print(program.dump())
        print("\n=== output ===")
    Interpreter().run(program)


def cmd_repl(args):
    interp = Interpreter()
    print("MiniLang REPL. Ctrl-D to exit.")
    buf, depth = [], 0
    while True:
        try:
            line = input("... " if buf else ">>> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        depth += line.count("{") - line.count("}")
        buf.append(line)
        if depth > 0:
            continue  # inside an unfinished if/while block; keep reading
        src = "\n".join(buf)
        buf, depth = [], 0
        if not src.strip():
            continue
        try:
            interp.run(parse(src))
        except LangError as e:
            print(f"Error: {e}")


def cmd_show(args):
    name = args[0].upper()
    pat = dict(TOKEN_RULES)[name]
    nfa, dfa, mdfa = compile_regular_expression(pat)
    print(f"token {name} = /{esc(pat)}/")
    print(f"  NFA (Thompson): {nfa.n} states")
    print_dfa("DFA (subset construction)", dfa)
    print_dfa("minimal DFA (partition refinement)", mdfa)
    if "--dot" in args:
        open(f"{name.lower()}.dot", "w").write(mdfa.to_dot(name))
        print(f"  wrote {name.lower()}.dot  (dot -Tpng {name.lower()}.dot -o {name.lower()}.png)")


def cmd_regular_expression(args):
    nfa, dfa, mdfa = compile_regular_expression(args[0])
    print(f"/{args[0]}/  NFA {nfa.n} -> DFA {dfa.n} -> minimal {mdfa.n} states")
    print_dfa("minimal DFA", mdfa)
    for s in args[1:]:
        print(f"  {s!r:<12} {'ACCEPT' if mdfa.run(s) else 'REJECT'}")


def cmd_tm(args):
    tm = TuringMachine(args[0], args[1])
    print(f"=== {tm.name} on {args[1]!r} ===")
    verdict, steps, state, tape = tm.run(show="--quiet" not in args)
    print(f"{verdict} after {steps} steps in state {state!r}, final tape {tape!r}")


def main():
    cmds = {"run": cmd_run, "repl": cmd_repl, "show": cmd_show, "regular-expression": cmd_regular_expression, "tm": cmd_tm}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(USAGE)
        sys.exit(1)
    if sys.argv[1] != "repl" and len(sys.argv) < 3:
        print(USAGE)
        sys.exit(1)
    try:
        cmds[sys.argv[1]](sys.argv[2:])
    except (LangError, ValueError, KeyError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
