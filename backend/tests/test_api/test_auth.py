"""Test authentication endpoints."""

import pytest


@pytest.mark.parametrize(
    "provider, expected_domain",
    [
        ("huawei", "huawei.com"),
        ("wechat", "open.weixin.qq.com"),
    ]
)
def test_auth_redirect(client, provider, expected_domain):
    """Test that login redirects to OAuth provider."""
    response = client.get(f"/auth/{provider}", follow_redirects=False)
    assert response.status_code == 307  # Temporary redirect
    assert expected_domain in response.headers["location"]


@pytest.mark.parametrize(
    "provider",
    [
        "huawei",
        "wechat",
    ]
)
def test_auth_callback_missing_code(client, provider):
    """Test callback with missing code parameter returns 422."""
    response = client.get(f"/auth/{provider}/callback", follow_redirects=False)
    # FastAPI will return 422 for missing required query param
    assert response.status_code == 422
