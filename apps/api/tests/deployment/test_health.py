from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def make_mock_engine(section_count=42):
    mock_result = MagicMock()
    mock_result.scalar.return_value = section_count

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_result)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx
    return mock_engine


def make_client(section_count=42):
    """Return a TestClient with the DB engine mocked on app.state."""
    from main import app

    app.state.engine = make_mock_engine(section_count)
    app.state.session_factory = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


def test_health_returns_200_when_db_reachable():
    client = make_client(section_count=100)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert data["sections"] == 100


def test_health_returns_503_when_db_unreachable():
    from main import app

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx

    app.state.engine = mock_engine
    app.state.session_factory = MagicMock()

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_version_returns_env_and_term():
    client = make_client()
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "env" in data
    assert "term" in data
