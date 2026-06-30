from core.domain.month_format import chart_point_label, format_month_year_label


def test_format_month_year_label():
    assert format_month_year_label(2026, 1) == "Jan/2026"
    assert format_month_year_label(2026, 3) == "Mar/2026"
    assert format_month_year_label(2026, 12) == "Dez/2026"


def test_chart_point_label_from_fields():
    assert chart_point_label({"year": 2026, "month": 2, "label": "02/2026"}) == "Fev/2026"