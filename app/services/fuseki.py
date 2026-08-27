from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class FusekiUpdateError(RuntimeError):
    pass


class FusekiClient:
    def __init__(
        self,
        base_url: str,
        dataset: str,
        *,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.update_url = f"{base_url.rstrip('/')}/{quote(dataset, safe='')}/update"
        self.timeout_seconds = timeout_seconds

    def update(self, sparql: str) -> None:
        request = Request(
            self.update_url,
            data=sparql.encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/sparql-update; charset=utf-8",
                "User-Agent": "problem-bank-graph-sync/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response.read()
        except HTTPError as error:
            response_body = error.read(1000).decode("utf-8", errors="replace")
            raise FusekiUpdateError(
                f"Fuseki가 HTTP {error.code}을 반환했습니다: {response_body}"
            ) from error
        except (TimeoutError, URLError) as error:
            raise FusekiUpdateError(f"Fuseki에 연결할 수 없습니다: {error}") from error
