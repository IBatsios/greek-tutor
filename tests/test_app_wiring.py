"""Import-level smoke test: the app builds and the Harada routes are mounted."""
from app.main import app


def test_harada_routes_are_mounted():
    paths = set(app.openapi()["paths"])
    assert {"/api/harada", "/api/harada/goal", "/api/harada/routine",
            "/api/harada/recompute", "/api/session/start"} <= paths
