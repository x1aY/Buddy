"""Test authentication endpoints."""


def test_auth_huawei_redirect(client):
    """Test that Huawei login redirects to OAuth provider."""
    response = client.get("/auth/huawei", follow_redirects=False)
    assert response.status_code == 307  # Temporary redirect
    assert "huawei.com" in response.headers["location"]
    assert "oauth" in response.headers["location"]


def test_auth_wechat_redirect(client):
    """Test that WeChat login redirects to OAuth provider."""
    response = client.get("/auth/wechat", follow_redirects=False)
    assert response.status_code == 307  # Temporary redirect
    assert "open.weixin.qq.com" in response.headers["location"]


def test_auth_huawei_callback_missing_code(client):
    """Test Huawei callback with missing code parameter returns error redirect."""
    response = client.get("/auth/huawei/callback", follow_redirects=False)
    # FastAPI will return 422 for missing required query param
    assert response.status_code == 422


def test_auth_wechat_callback_missing_code(client):
    """Test WeChat callback with missing code parameter returns error redirect."""
    response = client.get("/auth/wechat/callback", follow_redirects=False)
    # FastAPI will return 422 for missing required query param
    assert response.status_code == 422
