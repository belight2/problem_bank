from app.services.fuseki import FusekiClient


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return b""


def test_fuseki_client_posts_sparql_update(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.services.fuseki.urlopen", fake_urlopen)
    client = FusekiClient(
        "http://localhost:3030/",
        "problem-bank",
        timeout_seconds=3,
    )

    client.update("INSERT DATA { <urn:a> <urn:b> <urn:c> }")

    request = captured["request"]
    assert request.full_url == "http://localhost:3030/problem-bank/update"
    assert request.method == "POST"
    assert request.data == b"INSERT DATA { <urn:a> <urn:b> <urn:c> }"
    assert request.headers["Content-type"] == "application/sparql-update; charset=utf-8"
    assert captured["timeout"] == 3
