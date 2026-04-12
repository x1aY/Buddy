"""Third-party OAuth authentication"""
from .huawei_oauth import HuaweiOAuthService
from .wechat_oauth import WeChatOAuthService

__all__ = [
    'HuaweiOAuthService',
    'WeChatOAuthService',
]
