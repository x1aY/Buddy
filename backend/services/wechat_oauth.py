import httpx
from typing import Optional
from config import settings
from models.schemas import UserInfo


class WeChatOAuthService:
    OAUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
    TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
    USER_INFO_URL = "https://api.weixin.qq.com/sns/userinfo"

    @classmethod
    def get_authorization_url(cls) -> str:
        return f"{cls.OAUTH_URL}?appid={settings.wechat_app_id}&redirect_uri={settings.wechat_redirect_uri}&response_type=code&scope=snsapi_login"

    @classmethod
    async def get_access_token(cls, code: str) -> Optional[str]:
        if not settings.wechat_app_id or not settings.wechat_app_secret:
            return None

        params = {
            "appid": settings.wechat_app_id,
            "secret": settings.wechat_app_secret,
            "code": code,
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(cls.TOKEN_URL, params=params)
            if response.status_code != 200:
                return None

            result = response.json()
            return result.get("access_token")

    @classmethod
    async def get_user_info(cls, access_token: str, openid: str) -> Optional[UserInfo]:
        params = {
            "access_token": access_token,
            "openid": openid,
            "lang": "zh_CN"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(cls.USER_INFO_URL, params=params)
            if response.status_code != 200:
                return None

            result = response.json()
            if result.get("errcode"):
                return None

            return UserInfo(
                id=result.get("openid", ""),
                name=result.get("nickname", "WeChat User"),
                avatar=result.get("headimgurl", ""),
                provider="wechat"
            )
