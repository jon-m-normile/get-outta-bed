from .logic import PUZZLE_KEYS, choose_puzzle  # noqa: F401


def create(key: str, ctx):
    if key == "jigsaw":
        from .jigsaw import Jigsaw as cls
    elif key == "balloon":
        from .balloon import BalloonPop as cls
    elif key == "math":
        from .math_puzzle import MathPuzzle as cls
    else:
        from .simon import Simon as cls
    return cls(ctx)
