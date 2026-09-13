"""Derived non-JSON response regression. Original response body was unavailable."""

from regression_subject import decode_response


def test_non_json_response_is_explicitly_unknown():
    try:
        result = decode_response("<html>Unavailable</html>")
    except ValueError:
        result = {"status": "uncaught-parser-error"}
    assert result["status"] == "inconclusive", "non-JSON response must remain inconclusive"


def test_valid_json_negative_control():
    assert decode_response('{"value":3}') == {"status": "parsed", "value": {"value": 3}}


def test_empty_response():
    try:
        result = decode_response("")
    except ValueError:
        result = {"status": "uncaught-parser-error"}
    assert result["status"] == "inconclusive", "empty response must remain inconclusive"
