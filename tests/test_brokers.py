"""Broker autocomplete."""

from core.integrations.brokers import search_brokers


def test_search_brokers_prefix():
    matches = search_brokers("xp")
    assert "XP Investimentos" in matches


def test_search_brokers_min_length():
    assert search_brokers("x") == []