"""Unit tests for the duck-typed request context builder.

No FastAPI required: a tiny fake request that quacks like a Starlette Request.
"""

from g8scope_fastapi import request_context


class _Headers:
    def __init__(self, data):
        self._data = data

    def items(self):
        return self._data.items()


class _FakeRequest:
    def __init__(self, method, url, headers):
        self.method = method
        self.url = url
        self.headers = _Headers(headers)


def test_builds_method_and_url():
    req = _FakeRequest("POST", "http://test/items?q=1", {"accept": "application/json"})
    ctx = request_context(req)
    assert ctx["request"]["method"] == "POST"
    assert ctx["request"]["url"] == "http://test/items?q=1"
    assert ctx["custom"] == {}


def test_strips_authorization_and_cookie_headers():
    req = _FakeRequest(
        "GET",
        "http://test/",
        {
            "authorization": "Bearer secret",
            "Cookie": "session=abc",
            "x-custom": "keep-me",
            "user-agent": "pytest",
        },
    )
    headers = request_context(req)["request"]["headers"]
    assert "authorization" not in {k.lower() for k in headers}
    assert "cookie" not in {k.lower() for k in headers}
    assert headers["x-custom"] == "keep-me"
    assert headers["user-agent"] == "pytest"


def test_tolerates_an_exploding_request():
    class Exploding:
        @property
        def method(self):
            raise RuntimeError("boom")

    # An attribute that raises must degrade to the safe fallback, not propagate.
    ctx = request_context(Exploding())
    assert ctx == {"custom": {}}


def test_tolerates_a_bare_object():
    # A bare object has no request attributes; we still produce a valid,
    # non-raising context with empty fields.
    ctx = request_context(object())
    assert ctx["custom"] == {}
    assert ctx["request"] == {"method": "", "url": "", "headers": {}}


def test_tolerates_missing_headers():
    class NoHeaders:
        method = "GET"
        url = "http://test/"

    ctx = request_context(NoHeaders())
    assert ctx["request"]["headers"] == {}
    assert ctx["request"]["method"] == "GET"
