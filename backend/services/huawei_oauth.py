import httpx
from typing import Optional, Tuple
from config import settings
from models.schemas import UserInfo


class HuaweiOAuthService:
    OAUTH_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/authorize"
    TOKEN_URL = "https://oauth-login.cloud.huawei.com/oauth2/v3/token"
    USER_INFO_URL = "https://connect-api.cloud.huawei.com/api/profile/v1/me"

    @classmethod
    def get_authorization_url(cls) -> str:
        return f"{cls.OAUTH_URL}?client_id={settings.huawei_client_id}&redirect_uri={settings.huawei_redirect_uri}&response_type=code&scope=openid+profile"

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[str]:
        if not settings.huawei_client_id or not settings.huawei_client_secret:
            return None

        data = {
            "grant_type": "authorization_code",
            "client_id": settings.huawei_client_id,
            "client_secret": settings.huawei_client_secret,
            "code": code,
            "redirect_uri": settings.huawei_redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(cls.TOKEN_URL, data=data)
            if response.status_code != 200:
                return None

            result = response.json()
            return result.get("access_token")

    @classmethod
    async def get_user_info(cls, access_token: str) -> Optional[UserInfo]:
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(cls.USER_INFO_URL, headers=headers)
            if response.status_code != 200:
                return None

            result = response.json()
            if result.get("retCode") != 0:
                return None

            profile = result.get("profile", {})
            return UserInfo(
                id=str(profile.get("openId", "")),
                name=profile.get("displayName", "Huawei User"),
                avatar=profile.get("avatar", ""),
                provider="huawei"
            )
