from starlette.requests import Request

from backend.app.security.ratelimit import get_real_ip


def _make_request(headers=None, client_ip="10.0.0.1"):
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": (client_ip, 1234),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    if headers:
        scope["headers"] = [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ]
    return Request(scope)


def test_get_real_ip_prefers_x_forwarded_for_header():
    request = _make_request({"x-forwarded-for": "203.0.113.1, 70.0.0.1"}, client_ip="192.0.2.10")

    assert get_real_ip(request) == "203.0.113.1"


def test_get_real_ip_falls_back_to_client_ip():
    request = _make_request(client_ip="198.51.100.5")

    assert get_real_ip(request) == "198.51.100.5"
