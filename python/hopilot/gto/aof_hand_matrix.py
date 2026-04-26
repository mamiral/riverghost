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


def hand_coordinates_from_key(hand_key: str) -> tuple[int, int]:
    normalized = hand_key.strip()
    if len(normalized) == 2 and normalized[0] == normalized[1]:
        index = RANKS.index(normalized[0])
        return index, index

    if len(normalized) != 3 or normalized[2] not in ("s", "o"):
        raise ValueError(f"Unsupported canonical hand key: {hand_key!r}")

    high_rank = normalized[0]
    low_rank = normalized[1]
    if high_rank == low_rank:
        raise ValueError(f"Pairs must not include suitedness suffixes: {hand_key!r}")

    high_index = RANKS.index(high_rank)
    low_index = RANKS.index(low_rank)
    if normalized[2] == "s":
        return high_index, low_index
    return low_index, high_index


def hand_key_from_hole_cards(hole_cards: str | list[str] | tuple[str, str]) -> str:
    if isinstance(hole_cards, str):
        if len(hole_cards) != 4:
            raise ValueError(f"Expected 4-character hole cards string, got: {hole_cards!r}")
        cards = [hole_cards[:2], hole_cards[2:]]
    else:
        cards = list(hole_cards)

    if len(cards) != 2:
        raise ValueError("Exactly two hole cards are required")

    rank_one, suit_one = cards[0][0], cards[0][1]
    rank_two, suit_two = cards[1][0], cards[1][1]

    if rank_one == rank_two:
        return f"{rank_one}{rank_two}"

    ordered_ranks = sorted((rank_one, rank_two), key=RANKS.index)
    suitedness = "s" if suit_one == suit_two else "o"
    return f"{ordered_ranks[0]}{ordered_ranks[1]}{suitedness}"


def hand_coordinates_from_hole_cards(hole_cards: str | list[str] | tuple[str, str]) -> tuple[int, int]:
    return hand_coordinates_from_key(hand_key_from_hole_cards(hole_cards))


def iter_canonical_matrix_cells() -> list[tuple[int, int, str]]:
    return [
        (row_index, col_index, hand_key_from_index(row_index, col_index))
        for row_index in range(13)
        for col_index in range(13)
    ]


def format_metric_value(metric: str, value: float | None) -> str:
    if value is None:
        return "--"
    if metric in ("WIN_LOSE_PROBABILITY", "EQUITY"):
        return f"{_clamp_01(value) * 100:.1f}%"
    if metric in ("EV", "EQR"):
        return f"{value:+.2f}"
    return f"{value:.3f}"
