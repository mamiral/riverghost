import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gui_components.aof_hand_matrix_panel import AoFHandMatrixPanel


def test_ev_color_mapping_has_nested_positive_negative_tiers():
    panel = AoFHandMatrixPanel(0, 0)

    assert panel._ev_color(0.0, pot_size=1.0, bet_amount=1.0) == (150, 150, 150)
    assert panel._ev_color(0.25, pot_size=1.0, bet_amount=1.0) == (150, 150, 150)
    assert panel._ev_color(0.50, pot_size=1.0, bet_amount=1.0) == (160, 190, 120)
    assert panel._ev_color(0.75, pot_size=1.0, bet_amount=1.0) == (160, 190, 120)
    assert panel._ev_color(1.0, pot_size=1.0, bet_amount=1.0) == (110, 180, 100)
    assert panel._ev_color(1.25, pot_size=1.0, bet_amount=1.0) == (110, 180, 100)
    assert panel._ev_color(1.50, pot_size=1.0, bet_amount=1.0) == (80, 175, 90)
    assert panel._ev_color(2.0, pot_size=1.0, bet_amount=1.0) == (80, 175, 90)
    assert panel._ev_color(-0.05, pot_size=1.0, bet_amount=1.0) == (192, 60, 65)
    assert panel._ev_color(-1.0, pot_size=1.0, bet_amount=1.0) == (192, 60, 65)
