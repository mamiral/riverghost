RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


def hand_key_from_index(row: int, col: int) -> str:
    r1 = RANKS[row]
    r2 = RANKS[col]
    if row == col:
        return f"{r1}{r2}"
    if row < col:
        return f"{r1}{r2}s"
    return f"{r2}{r1}o"


def build_matrix_keys() -> list[list[str]]:
    return [[hand_key_from_index(r, c) for c in range(13)] for r in range(13)]


def format_metric_value(metric: str, value: float | None) -> str:
    if value is None:
        return "--"
    if metric in ("WIN_LOSE_PROBABILITY", "EQUITY", "EQR"):
        return f"{_clamp_01(value) * 100:.1f}%"
    if metric == "EV":
        return f"{value:+.2f}"
    return f"{value:.3f}"
