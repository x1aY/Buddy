from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from services import HuaweiOAuthService, WeChatOAuthService
from utils.jwt import create_jwt_token
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/huawei")
async def login_huawei():
    """Redirect to Huawei OAuth"""
    url = HuaweiOAuthService.get_authorization_url()
    return RedirectResponse(url)


@router.get("/huawei/callback")
async def huawei_callback(request: Request, code: str):
    """Huawei OAuth callback"""
    access_token = await HuaweiOAuthService.get_access_token(code)
    if not access_token:
        return RedirectResponse(f"{request.base_url}login?error=auth_failed")

    user_info = await HuaweiOAuthService.get_user_info(access_token)
    if not user_info:
        return RedirectResponse(f"{request.base_url}login?error=user_info_failed")

    token = create_jwt_token(user_info)
    encoded_user = user_info.model_dump_json()

    # Redirect back to frontend with token
    frontend_url = settings.cors_allow_origins.split(",")[0]
    return RedirectResponse(f"{frontend_url}/#/login?token={token}&user={encoded_user}")


@router.get("/wechat")
async def login_wechat():
    """Redirect to WeChat OAuth"""
    url = WeChatOAuthService.get_authorization_url()
    return RedirectResponse(url)


@router.get("/wechat/callback")
async def wechat_callback(request: Request, code: str):
    """WeChat OAuth callback"""
    import httpx

    if not settings.wechat_app_id or not settings.wechat_app_secret:
        return RedirectResponse(f"{request.base_url}login?error=config_missing")

    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "code": code,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.weixin.qq.com/sns/oauth2/access_token", params=params)
        if response.status_code != 200:
            return RedirectResponse(f"{request.base_url}login?error=auth_failed")

        result = response.json()
        access_token = result.get("access_token")
        openid = result.get("openid")

        if not access_token or not openid:
            return RedirectResponse(f"{request.base_url}login?error=auth_failed")

        user_info = await WeChatOAuthService.get_user_info(access_token, openid)
        if not user_info:
            return RedirectResponse(f"{request.base_url}login?error=user_info_failed")

        token = create_jwt_token(user_info)
        encoded_user = user_info.model_dump_json()

        frontend_url = settings.cors_allow_origins.split(",")[0]
        return RedirectResponse(f"{frontend_url}/#/login?token={token}&user={encoded_user}")
