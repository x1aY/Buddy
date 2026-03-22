"""Test root endpoint."""


def test_root_get(client):
    """Test that root endpoint returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert data["status"] == "ok"
