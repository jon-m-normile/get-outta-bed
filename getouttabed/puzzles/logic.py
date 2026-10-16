"""UI-independent puzzle state, so it can be unit tested."""
import random
from typing import List, Optional

PUZZLE_KEYS = ["jigsaw", "sliding", "balloon", "math", "simon"]
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


class SlidingLogic:
    """board[pos] = tile index; the gap is tile n-1 (bottom-right)."""

    def __init__(self, size: int = 3, rng=random, min_moves: int = 15, max_moves: int = 25):
        self.size, self.rng = size, rng
        self.min_moves, self.max_moves = min_moves, max_moves
        self.gap_tile = size * size - 1
        self.board: List[int] = []
        self.scramble()

    @property
    def gap(self) -> int:
        return self.board.index(self.gap_tile)

    def neighbors(self, pos: int) -> List[int]:
        r, c = divmod(pos, self.size)
        out = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            rr, cc = r + dr, c + dc
            if 0 <= rr < self.size and 0 <= cc < self.size:
                out.append(rr * self.size + cc)
        return out

    def scramble(self) -> None:
        self.board = list(range(self.size * self.size))
        self.moves_made = 0
        target = self.rng.randint(self.min_moves, self.max_moves)
        prev = None
        while self.moves_made < target or self.solved:
            options = [p for p in self.neighbors(self.gap) if p != prev]
            pick = self.rng.choice(options)
            prev = self.gap
            self.move(pick)
            self.moves_made += 1

    def can_move(self, pos: int) -> bool:
        return pos in self.neighbors(self.gap)

    def move(self, pos: int) -> bool:
        if not self.can_move(pos):
            return False
        g = self.gap
        self.board[g], self.board[pos] = self.board[pos], self.board[g]
        return True

    def move_direction(self, direction: str) -> bool:
        """Arrow keys move the tile that sits opposite the arrow into the gap."""
        r, c = divmod(self.gap, self.size)
        dr, dc = {"up": (1, 0), "down": (-1, 0), "left": (0, 1), "right": (0, -1)}[direction]
        rr, cc = r + dr, c + dc
        if 0 <= rr < self.size and 0 <= cc < self.size:
            return self.move(rr * self.size + cc)
        return False

    def is_solvable(self) -> bool:
        tiles = [t for t in self.board if t != self.gap_tile]
        inversions = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])
        if self.size % 2 == 1:
            return inversions % 2 == 0
        gap_row_from_bottom = self.size - self.gap // self.size
        return (inversions + gap_row_from_bottom) % 2 == 1

    @property
    def solved(self) -> bool:
        return self.board == list(range(self.size * self.size))


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
