import os, sys
# add project root to path so imports work regardless of invocation
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from utils import calculate_average_score, adjust_difficulty, generate_new_round


def test_calculate_average_score():
    assert calculate_average_score([100, 80, 60]) == pytest.approx(80)
    assert calculate_average_score([]) == 0


def test_adjust_difficulty():
    assert adjust_difficulty(1, 90) == 2
    assert adjust_difficulty(3, 40) == 2
    assert adjust_difficulty(1, 40) == 1


def test_generate_new_round():
    res = generate_new_round(1, [90,85,95])
    assert res['round_level'] == 2
    assert res['average_score'] == pytest.approx(90)
