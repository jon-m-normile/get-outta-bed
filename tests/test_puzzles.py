import random

from getouttabed.puzzles.logic import (JigsawLogic, MathLogic, MathProblem, SimonLogic, SlidingLogic,
                                       choose_puzzle, make_problem, BalloonLogic, PUZZLE_KEYS)


def test_jigsaw_never_solved_and_6_misplaced():
    for seed in range(500):
        j = JigsawLogic(rng=random.Random(seed))
        assert not j.solved and j.misplaced() >= 6
        assert sorted(j.board) == list(range(9))


def test_jigsaw_swap_to_solve():
    j = JigsawLogic(rng=random.Random(3))
    for pos in range(9):
        j.swap(pos, j.board.index(pos))
    assert j.solved


def test_sliding_always_solvable_and_scrambled():
    for seed in range(500):
        s = SlidingLogic(rng=random.Random(seed))
        assert s.is_solvable() and not s.solved
        assert 15 <= s.moves_made <= 27


def test_sliding_unsolvable_detected():
    s = SlidingLogic(rng=random.Random(0))
    s.board = [1, 0, 2, 3, 4, 5, 6, 7, 8]
    assert not s.is_solvable()


def test_sliding_moves():
    s = SlidingLogic(rng=random.Random(0))
    s.board = list(range(9))
    s.board[7], s.board[8] = 8, 7  # gap at 7
    assert not s.move(0)
    assert s.move_direction("left")  # tile right of gap moves left
    assert s.solved


def test_math_checker():
    p = MathProblem(47, "+", 38)
    assert p.check("85") and p.check(" 85 ") and not p.check("84") and not p.check("") and not p.check("abc")
    assert MathProblem(50, "−", 50).check("0")
    assert MathProblem(7, "×", 8).check("56")


def test_math_ranges():
    rng = random.Random(7)
    for _ in range(2000):
        p = make_problem(rng)
        assert 0 <= p.answer <= 199
        if p.op == "×":
            assert p.a < 10 and p.b < 10
        else:
            assert 10 <= p.a <= 99 and 10 <= p.b <= 99


def test_math_flow_and_fairness():
    m = MathLogic(rng=random.Random(1))
    assert m.submit(str(m.current.answer)) == "correct"
    first = m.current
    assert m.submit("-999") == "wrong" and m.current is not first
    assert m.submit("-999") == "wrong"
    assert m.submit("-999") == "reset" and m.index == 0
    for _ in range(3):
        res = m.submit(str(m.current.answer))
    assert res == "solved" and m.solved


def test_simon_sequence_compare():
    assert SimonLogic.matches([0, 1, 2, 3, 0], [0, 1, 2, 3, 0])
    assert not SimonLogic.matches([0, 1, 2, 3, 0], [0, 1, 2, 3, 1])
    assert not SimonLogic.matches([0, 1], [0])


def test_simon_flow_and_fairness():
    s = SimonLogic(rng=random.Random(2))
    seq = list(s.sequence)
    assert len(seq) == 5 and all(0 <= p < 4 for p in seq)
    wrong = (seq[0] + 1) % 4
    assert s.press(wrong) == "mistake" and s.sequence == seq
    assert s.press(wrong) == "mistake"
    assert s.press(wrong) == "reset" and s.failures == 0
    for i, p in enumerate(s.sequence):
        res = s.press(p)
    assert res == "solved"


def test_balloon():
    b = BalloonLogic()
    assert not any(b.pop() for _ in range(9))
    assert b.pop()


def test_surprise_never_repeats_last():
    rng = random.Random(0)
    last = None
    for _ in range(300):
        pick = choose_puzzle("surprise", last, rng)
        assert pick in PUZZLE_KEYS and pick != last
        last = pick
    assert choose_puzzle("math", "math") == "math"
