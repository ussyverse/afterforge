"""Derived search-schema regression; fixtures are synthetic contract shapes."""

from regression_subject import search_output


def test_grouped_search_shape():
    try:
        result = search_output({"total_count": 1, "matches_text": "module.py:1: definition"})
    except KeyError:
        result = None
    assert result == "module.py:1: definition", "grouped search must not require matches key"


def test_legacy_search_control():
    assert search_output({"matches": ["definition"]}) == ["definition"]


def test_empty_search():
    try:
        result = search_output({"total_count": 0})
    except KeyError:
        result = None
    assert result == "", "empty search is not an exception"
