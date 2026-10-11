from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

ALLOWED_ORIGIN = get_settings().cors_origin_list[0]
HEALTH = "/api/v1/health"


def test_exposes_the_download_file_name_to_the_allowed_origin() -> None:
    response = TestClient(app).get(HEALTH, headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-expose-headers"] == "Content-Disposition"


def test_does_not_allow_an_unknown_origin() -> None:
    response = TestClient(app).get(HEALTH, headers={"Origin": "https://unknown.example.org"})

    assert "access-control-allow-origin" not in response.headers
