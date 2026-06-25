"""Integration + unit tests for the g8scope FastAPI adapter.

A FakeTransport records shipped envelopes — no network. Where FastAPI/Starlette
are installed (the preferred path) we drive a real app via the TestClient.
"""

import pytest

from g8scope import Client, Config, Transport

from g8scope_fastapi import (
    G8ScopeMiddleware,
    add_g8scope,
    request_context,
)

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402


class FakeTransport(Transport):
    """Records sent envelopes; no network."""

    def __init__(self):
        self.sent = []

    def send(self, endpoint, key, envelope, timeout):
        self.sent.append(
            {"endpoint": endpoint, "key": key, "envelope": envelope, "timeout": timeout}
        )


def _app(client):
    app = FastAPI()
    app.add_middleware(G8ScopeMiddleware, client=client)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def test_captures_unhandled_exception_and_ships_envelope():
    t = FakeTransport()
    client = Client(Config(key="k", base_path="/srv/app"), t)
    # raise_server_exceptions=False so FastAPI's 500 path runs instead of
    # re-raising into the test client.
    with TestClient(_app(client), raise_server_exceptions=False) as tc:
        resp = tc.get("/boom")

    assert resp.status_code == 500
    assert len(t.sent) == 1
    env = t.sent[0]["envelope"]
    assert env["runtime"]["name"] == "python"
    assert env["sdk"]["name"] == "g8scope-python"
    assert env["sdk"]["version"]
    assert env["exception"]["type"] == "RuntimeError"
    assert env["exception"]["message"] == "kaboom"
    assert "project" not in env  # resolved server-side from the key
    # request context made it through
    assert env["context"]["request"]["method"] == "GET"
    assert env["context"]["request"]["url"].endswith("/boom")


def test_successful_request_ships_nothing():
    t = FakeTransport()
    client = Client(Config(key="k"), t)
    with TestClient(_app(client)) as tc:
        resp = tc.get("/ok")

    assert resp.status_code == 200
    assert t.sent == []


def test_disabled_client_sends_nothing_but_still_500s():
    t = FakeTransport()
    client = Client(Config(key="k", enabled=False), t)
    with TestClient(_app(client), raise_server_exceptions=False) as tc:
        resp = tc.get("/boom")

    assert resp.status_code == 500
    assert t.sent == []


def test_no_key_sends_nothing():
    t = FakeTransport()
    client = Client(Config(key=None), t)
    with TestClient(_app(client), raise_server_exceptions=False) as tc:
        resp = tc.get("/boom")

    assert resp.status_code == 500
    assert t.sent == []


def test_add_g8scope_helper_registers_middleware():
    t = FakeTransport()
    client = Client(Config(key="k"), t)
    app = FastAPI()
    add_g8scope(app, client=client)

    @app.get("/boom")
    def boom():
        raise ValueError("via helper")

    with TestClient(app, raise_server_exceptions=False) as tc:
        resp = tc.get("/boom")

    assert resp.status_code == 500
    assert len(t.sent) == 1
    assert t.sent[0]["envelope"]["exception"]["type"] == "ValueError"


def test_broken_transport_never_breaks_the_response_flow():
    class BrokenTransport(Transport):
        def send(self, endpoint, key, envelope, timeout):
            raise RuntimeError("transport exploded")

    client = Client(Config(key="k"), BrokenTransport())
    with TestClient(_app(client), raise_server_exceptions=False) as tc:
        resp = tc.get("/boom")

    # Host app's error handling still runs; capture failure is swallowed.
    assert resp.status_code == 500
