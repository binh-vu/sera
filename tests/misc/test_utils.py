import pytest

from sera.misc import to_kebab_case, to_snake_case


@pytest.mark.parametrize(
    "source,expected",
    [
        ("simple", "simple"),  # already lower
        ("already_snake", "already_snake"),  # idempotent
        ("camelCase", "camel_case"),
        ("PascalCase", "pascal_case"),
        ("XMLHttpRequest", "xml_http_request"),  # leading & mid acronym
        ("parseHTTPResponse", "parse_http_response"),  # mid acronym then normal word
        ("HTTPRequest", "http_request"),  # ending acronym separated from trailing word
        ("URL", "url"),  # pure acronym
        ("Version2ID", "version2_id"),  # digits inside & trailing acronym
        ("HTTP2Server", "http2_server"),  # acronym + digit + word
        ("X", "x"),  # single letter
        ("kebab-case", "kebab_case"),
    ],
)
def test_to_snake_case_basic(source: str, expected: str):
    assert to_snake_case(source) == expected


@pytest.mark.parametrize(
    "source,expected",
    [
        ("simple", "simple"),  # already lower
        ("already-kebab", "already-kebab"),  # idempotent
        ("camelCase", "camel-case"),
        ("PascalCase", "pascal-case"),
        ("XMLHttpRequest", "xml-http-request"),  # leading & mid acronym
        ("parseHTTPResponse", "parse-http-response"),  # mid acronym then normal word
        ("HTTPRequest", "http-request"),  # ending acronym separated from trailing word
        ("URL", "url"),  # pure acronym
        ("Version2ID", "version2-id"),  # digits inside & trailing acronym
        ("HTTP2Server", "http2-server"),  # acronym + digit + word
        ("X", "x"),  # single letter
        ("snake_case", "snake-case"),
    ],
)
def test_to_kebab_case_basic(source: str, expected: str):
    assert to_kebab_case(source) == expected
