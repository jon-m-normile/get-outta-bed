"""UI-independent puzzle state, so it can be unit tested."""
import random
from typing import List, Optional

PUZZLE_KEYS = ["jigsaw", "balloon", "math", "simon"]
MAX_FAILURES = 3


def choose_puzzle(choice: str, last: Optional[str], rng=random) -> str:
    if choice in PUZZLE_KEYS:
        return choice
    return rng.choice([k for k in PUZZLE_KEYS if k != last])


class JigsawLogic:
    """board[pos] = tile index; solved when board[i] == i for all i."""

    MIN_MISPLACED = 6

    def __init__(self, size: int = 3, rng=random):
        self.size, self.rng = size, rng
        self.board: List[int] = []
        self.scramble()

    def scramble(self) -> None:
        n = self.size * self.size
        self.board = list(range(n))
        while self.misplaced() < self.MIN_MISPLACED:
            self.rng.shuffle(self.board)

    def misplaced(self) -> int:
        return sum(1 for i, t in enumerate(self.board) if i != t)

    def correct(self, pos: int) -> bool:
        return self.board[pos] == pos

    def swap(self, a: int, b: int) -> None:
        self.board[a], self.board[b] = self.board[b], self.board[a]

    @property
    def solved(self) -> bool:
        return self.misplaced() == 0


class MathProblem:
    def __init__(self, a: int, op: str, b: int):
        self.a, self.op, self.b = a, op, b

    @property
    def answer(self) -> int:
        return {"+": self.a + self.b, "−": self.a - self.b, "×": self.a * self.b}[self.op]

    def text(self) -> str:
        return f"{self.a} {self.op} {self.b} ="

    def check(self, typed: str) -> bool:
        typed = typed.strip().replace("−", "-")
        try:
            return int(typed) == self.answer
        except ValueError:
            return False


def make_problem(rng=random) -> MathProblem:
    kind = rng.choice(["+", "−", "×"])
    if kind == "+":
        return MathProblem(rng.randint(10, 99), "+", rng.randint(10, 99))
    if kind == "−":
        a, b = rng.randint(10, 99), rng.randint(10, 99)
        return MathProblem(max(a, b), "−", min(a, b))
    return MathProblem(rng.randint(2, 9), "×", rng.randint(2, 9))


class MathLogic:
    COUNT = 3

    def __init__(self, rng=random):
        self.rng = rng
        self.new_set()

    def new_set(self) -> None:
        self.problems = [make_problem(self.rng) for _ in range(self.COUNT)]
        self.index = 0
        self.wrong = 0

    @property
    def current(self) -> MathProblem:
        return self.problems[self.index]

    def submit(self, typed: str) -> str:
        """Returns 'correct', 'solved', 'wrong' (new problem) or 'reset' (new set)."""
        if self.current.check(typed):
            self.index += 1
            return "solved" if self.index >= self.COUNT else "correct"
        self.wrong += 1
        if self.wrong >= MAX_FAILURES:
            self.new_set()
            return "reset"
        self.problems[self.index] = make_problem(self.rng)
        return "wrong"

    @property
    def solved(self) -> bool:
        return self.index >= self.COUNT


class SimonLogic:
    LENGTH = 5
    PADS = 4

    def __init__(self, rng=random):
        self.rng = rng
        self.failures = 0
        self.new_sequence()

    def new_sequence(self) -> None:
        self.sequence = [self.rng.randrange(self.PADS) for _ in range(self.LENGTH)]
        self.failures = 0
        self.position = 0

    def press(self, pad: int) -> str:
        """Returns 'ok', 'solved', 'mistake' (replay same) or 'reset' (new sequence)."""
        if pad == self.sequence[self.position]:
            self.position += 1
            return "solved" if self.position >= self.LENGTH else "ok"
        self.position = 0
        self.failures += 1
        if self.failures >= MAX_FAILURES:
            self.new_sequence()
            return "reset"
        return "mistake"

    @staticmethod
    def matches(sequence: List[int], entered: List[int]) -> bool:
        return list(sequence) == list(entered)


class BalloonLogic:
    TARGET = 10

    def __init__(self):
        self.popped = 0

    def pop(self) -> bool:
        self.popped += 1
        return self.solved

    @property
    def solved(self) -> bool:
        return self.popped >= self.TARGET
