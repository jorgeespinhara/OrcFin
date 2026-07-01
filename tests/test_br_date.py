"""Brazilian date mask and parsing."""

from datetime import date

import pytest

from core.domain.br_date import format_br_date_input, parse_br_date


def test_date_mask():
    assert format_br_date_input("01022024") == "01/02/2024"
    assert format_br_date_input("01/02/2024") == "01/02/2024"


def test_parse_br_date():
    assert parse_br_date("01/02/2024") == date(2024, 2, 1)
    assert parse_br_date("2024-02-01") == date(2024, 2, 1)


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_br_date("32/13/2024")