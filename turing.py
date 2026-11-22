MACHINES = {
    "binary_increment": {
        "start": "q0", "accept": {"qaccept"}, "reject": set(), "head": 0,
        "trans": {
            "q0":     {"0": ("q0", "0", "R"), "1": ("q0", "1", "R"), "_": ("qcarry", "_", "L")},
            "qcarry": {"1": ("qcarry", "0", "L"), "0": ("qaccept", "1", "S"), "_": ("qaccept", "1", "S")},
        },
    },
    "binary_addition": {
        "start": "toPlus0", "accept": {"qaccept"}, "reject": set(), "head": "+",
        "trans": {
            "toPlus0":   {"0": ("toPlus0", "0", "R"), "1": ("toPlus0", "1", "R"), "+": ("checkzero", "+", "R")},
            "checkzero": {"0": ("checkzero", "0", "R"), "1": ("toBend", "1", "R"), "_": ("cleanup", "_", "L")},
            "toBend":    {"0": ("toBend", "0", "R"), "1": ("toBend", "1", "R"), "_": ("decB", "_", "L")},
            "decB":      {"1": ("toPlus", "0", "L"), "0": ("decB", "1", "L")},
            "toPlus":    {"0": ("toPlus", "0", "L"), "1": ("toPlus", "1", "L"), "+": ("incA", "+", "L")},
            "incA":      {"0": ("toPlus0", "1", "R"), "1": ("incA", "0", "L"), "_": ("toPlus0", "1", "R")},
            "cleanup":   {"0": ("cleanup", "_", "L"), "1": ("cleanup", "_", "L"), "+": ("qaccept", "_", "S")},
        },
    },
    "palindrome_check": {
        "start": "q0", "accept": {"qaccept"}, "reject": {"qreject"}, "head": 0,
        "trans": {
            "q0":  {"0": ("qR0", "_", "R"), "1": ("qR1", "_", "R"), "_": ("qaccept", "_", "S")},
            "qR0": {"0": ("qR0", "0", "R"), "1": ("qR0", "1", "R"), "_": ("qC0", "_", "L")},
            "qR1": {"0": ("qR1", "0", "R"), "1": ("qR1", "1", "R"), "_": ("qC1", "_", "L")},
            "qC0": {"0": ("qL", "_", "L"), "1": ("qreject", "1", "S"), "_": ("qaccept", "_", "S")},
            "qC1": {"1": ("qL", "_", "L"), "0": ("qreject", "0", "S"), "_": ("qaccept", "_", "S")},
            "qL":  {"0": ("qL", "0", "L"), "1": ("qL", "1", "L"), "_": ("q0", "_", "R")},
        },
    },
}


class TuringMachine:
    def __init__(self, name, input):
        spec = MACHINES[name]
        self.name, self.trans = name, spec["trans"]
        self.accept, self.reject = spec["accept"], spec["reject"]
        self.tape = {i: ch for i, ch in enumerate(input) if ch != "_"}
        self.head = input.index(spec["head"]) if isinstance(spec["head"], str) else spec["head"]
        self.state, self.steps = spec["start"], 0

    def step(self):
        if self.state in self.accept or self.state in self.reject:
            return False
        rule = self.trans.get(self.state, {}).get(self.tape.get(self.head, "_"))
        if rule is None:
            return False
        self.state, sym, move = rule
        if sym == "_":
            self.tape.pop(self.head, None)
        else:
            self.tape[self.head] = sym
        self.head += {"L": -1, "R": 1, "S": 0}[move]
        self.steps += 1
        return True

    def run(self, max_steps=100000, show=True):
        if show:
            self.show()
        while self.steps < max_steps and self.step():
            if show:
                self.show()
        if self.state in self.accept:
            verdict = "ACCEPTED"
        elif self.state in self.reject:
            verdict = "REJECTED"
        elif self.steps >= max_steps:
            verdict = "DID NOT HALT"
        else:
            verdict = "HALTED (no rule)"
        return verdict, self.steps, self.state, self.tape_str()

    def tape_str(self):
        if not self.tape:
            return ""
        lo, hi = min(self.tape), max(self.tape)
        return "".join(self.tape.get(i, "_") for i in range(lo, hi + 1))

    def show(self):
        lo = min(list(self.tape) + [self.head])
        hi = max(list(self.tape) + [self.head])
        cells = "".join(self.tape.get(i, "_") for i in range(lo, hi + 1))
        print(f"  step {self.steps:>4}  {self.state:<10} {cells}")
        print(f"  {'':>16} {' ' * (self.head - lo)}^")
