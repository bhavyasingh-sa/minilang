# MiniLang

A tiny programming language built from scratch in Python, using regular expressions, finite automata,
a context-free grammar and a Turing machine simulator.
Every stage of the pipeline is implemented by hand (no `re` module):

```
regular expression  --Thompson-->  ε-NFA  --subset construction-->  DFA  --partition refinement-->  minimal DFA
                                                                                          |
source code  --tokenizer (maximal munch over token DFAs)-->  tokens  --recursive-descent parser (CFG)-->  parse tree  --interpreter-->  output
```

plus a Turing machine simulator with three machines (binary increment, binary addition, palindrome check).
The `binary_addition` machine isn't just a standalone CLI demo -- it's not optional and not
behind any special syntax: the ordinary `+` operator in every MiniLang program is `lang.py`'s
`tm_add()`, which actually runs that Turing machine to compute the sum. See "Language" below.

## Files

| File | Contents | TOC concept |
|---|---|---|
| `automata.py` | regular expression parser, NFA, DFA, Thompson's construction, subset construction, DFA minimization | regular expressions, ε-NFA, NFA→DFA, minimization |
| `lang.py` | token rules → DFAs, tokenizer, parser, interpreter | finite automata in use, context-free grammar, parsing |
| `turing.py` | single-tape Turing machine simulator + 3 machines | Turing machines |
| `main.py` | command-line interface | — |
| `minilang_all.txt` | language feature reference + the 4 working examples and 2 bad examples, as text (not runnable files) | — |

## Usage

```
python3 main.py run <file>.ml               # a program you wrote yourself, or copied out of minilang_all.txt
python3 main.py run --verbose <file>.ml     # tokens, NFA/DFA/min-DFA sizes, parse tree, output
python3 main.py repl                        # interactive read-eval-print loop
python3 main.py show IDENT --dot            # tables for one token rule (+ Graphviz .dot)
python3 main.py regular-expression '(a|b)*abb' abb ab   # compile a regular expression, test strings
python3 main.py tm binary_addition 101+11   # animated tape: 5 + 3 -> 1000
python3 main.py tm palindrome_check 10101 --quiet
```

Python 3.8+, standard library only.

## Language

Integers, variables, `+ - * / %`, comparisons, unary `-`, parentheses, `x = expr`, `print expr`,
`if cond { } else { }`, `while cond { }`, `#` comments. The grammar is implemented in `lang.py`'s
`Parser` class (one method per production: `stmt`, `expr`, `arith`, `term`, `factor`, ...).

**`+` is computed by a real Turing machine, not Python arithmetic.** `lang.py`'s `tm_add(a, b)`
converts `a` and `b` to binary, builds a tape `"a_bits+b_bits"`, and runs `turing.py`'s
`binary_addition` machine on it to completion -- the sum is read off the tape when it halts.
Every `Interpreter.eval()` call for a `+` `BinOp` goes through this, so an ordinary loop like
`total = total + i` is genuinely running a Turing machine on every iteration, with no special
syntax. (Falls back to plain Python addition only when an operand is negative, since the
machine's transition table has no sign handling.) `-`, `*`, `/`, `%` remain ordinary Python
arithmetic. See `minilang_all.txt` section 12 for a worked example.
