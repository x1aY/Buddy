"""User session storage for login records using CSV."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Literal

from .csv_storage import CSVStorage

# Project root / backend/data/
DATA_DIR = Path(__file__).parent.parent / "data"


ProviderType = Literal['huawei', 'wechat']


@dataclass
class UserSession:
    """Represents a user login session."""
    session_id: str
    user_id: str
    username: str
    display_name: str
    provider: ProviderType
    login_time: str
    expires_at: str
    ip_address: Optional[str]


def user_session_to_dict(session: UserSession) -> dict:
    """Convert UserSession to CSV row dict."""
    return {
        'session_id': session.session_id,
        'user_id': session.user_id,
        'username': session.username,
        'display_name': session.display_name,
        'provider': session.provider,
        'login_time': session.login_time,
        'expires_at': session.expires_at,
        'ip_address': session.ip_address or '',
    }


def dict_to_user_session(row: dict) -> UserSession:
    """Convert CSV row dict to UserSession."""
    return UserSession(
        session_id=row.get('session_id', ''),
        user_id=row.get('user_id', ''),
        username=row.get('username', ''),
        display_name=row.get('display_name', ''),
        provider=row.get('provider', ''),
        login_time=row.get('login_time', ''),
        expires_at=row.get('expires_at', ''),
        ip_address=row.get('ip_address') or None,
    )


# Lazy initialized storage instance
_user_session_storage: CSVStorage[UserSession] | None = None


def _get_storage() -> CSVStorage[UserSession]:
    """Get or create the storage instance (lazy initialization)."""
    global _user_session_storage
    if _user_session_storage is None:
        _user_session_storage = CSVStorage[UserSession](
            file_path=DATA_DIR / "user_sessions.csv",
            headers=[
                'session_id',
                'user_id',
                'username',
                'display_name',
                'provider',
                'login_time',
                'expires_at',
                'ip_address',
            ],
            row_to_dict=user_session_to_dict,
            dict_to_row=dict_to_user_session
        )
    return _user_session_storage


def add_user_session(
    session_id: str,
    user_id: str,
    username: str,
    display_name: str,
    provider: ProviderType,
    login_time: datetime,
    expires_at: datetime,
    ip_address: Optional[str] = None
) -> UserSession:
    """Add a new user session to storage.

    Args:
        session_id: Unique session identifier
        user_id: User ID from OAuth provider
        username: Username
        display_name: Display name
        provider: OAuth provider ('huawei' or 'wechat')
        login_time: Login timestamp
        expires_at: Token expiration timestamp
        ip_address: Client IP address (optional)

    Returns:
        The created UserSession object
    """
    session = UserSession(
        session_id=session_id,
        user_id=user_id,
        username=username,
        display_name=display_name,
        provider=provider,
        login_time=login_time.isoformat(),
        expires_at=expires_at.isoformat(),
        ip_address=ip_address
    )
    storage = _get_storage()
    storage.append(session)
    return session


def get_all_sessions() -> List[UserSession]:
    """Get all stored user sessions.

    Returns:
        List of all user sessions
    """
    storage = _get_storage()
    return storage.load_all()


def count_sessions() -> int:
    """Get total number of sessions.

    Returns:
        Total count of sessions
    """
    storage = _get_storage()
    return storage.count()
