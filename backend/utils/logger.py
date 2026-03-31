"""Structured logging configuration."""

import json
import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

import structlog
from structlog.processors import add_log_level, TimeStamper, JSONRenderer

from config import settings

BASE_DIR = Path(__file__).parent.parent

# 日志轮转配置常量
LOG_ROTATION_WHEN = "W0"  # 每周一轮转（周一）
LOG_ROTATION_INTERVAL = 1  # 每周一次
LOG_FULL_BACKUP_COUNT = 1  # 完整日志保留1周
LOG_MAIN_BACKUP_COUNT = 2  # 关键日志保留2周

# 日志事件常量
EVENT_FRONTEND_CONNECTED = 'frontend_connected'
EVENT_FRONTEND_DISCONNECTED = 'frontend_disconnected'
EVENT_ASR_CONNECTION_READY = 'streaming_asr_connection_ready'
EVENT_ASR_START_FAILED = 'streaming_asr_start_failed'
EVENT_ASR_SESSION_STARTED = 'streaming_asr_session_started'
EVENT_ASR_STOPPED = 'streaming_asr_stopped'
EVENT_TRANSCRIPTION_STARTED = 'transcription_started'
EVENT_TRANSCRIPTION_FAILED = 'transcription_start_failed'
EVENT_ASR_CREDENTIALS_NOT_CONFIGURED = 'ASR credentials not configured'
EVENT_ALIYUN_TOKEN_EXPIRE = 'aliyun token expire time'
EVENT_DATA_TRANSFER_STATS = 'data_transfer_stats'
EVENT_AUDIO_STREAM_ACTIVE = 'audio_stream_active'
EVENT_VIDEO_STREAM_ACTIVE = 'video_stream_active'
EVENT_AUDIO_TOGGLED = 'audio_toggled'
EVENT_CAMERA_TOGGLED = 'camera_toggled'
EVENT_SUBTITLE_TOGGLED = 'subtitle_toggled'
EVENT_APPLICATION_STARTED = 'Application started'
EVENT_STARTING_UVICORN = 'Starting Uvicorn server'


class MainLogFilter(logging.Filter):
    """只让关键日志进入 log_main 的过滤器"""

    ALLOWED_EVENTS = {
        EVENT_FRONTEND_CONNECTED,
        EVENT_FRONTEND_DISCONNECTED,
        EVENT_ASR_CONNECTION_READY,
        EVENT_ASR_START_FAILED,
        EVENT_ASR_SESSION_STARTED,
        EVENT_ASR_STOPPED,
        EVENT_TRANSCRIPTION_STARTED,
        EVENT_TRANSCRIPTION_FAILED,
        EVENT_ASR_CREDENTIALS_NOT_CONFIGURED,
        EVENT_ALIYUN_TOKEN_EXPIRE,
        EVENT_DATA_TRANSFER_STATS,
        EVENT_AUDIO_STREAM_ACTIVE,
        EVENT_VIDEO_STREAM_ACTIVE,
        EVENT_AUDIO_TOGGLED,
        EVENT_CAMERA_TOGGLED,
        EVENT_SUBTITLE_TOGGLED,
        EVENT_APPLICATION_STARTED,
        EVENT_STARTING_UVICORN,
    }

    def filter(self, record):
        # ERROR/WARNING 总是保留
        if record.levelno >= logging.WARNING:
            return True

        # INFO 级别只保留允许的关键事件
        msg = record.getMessage()
        return any(event in msg for event in self.ALLOWED_EVENTS)


class MainLogFormatter(logging.Formatter):
    """log_main 的自定义格式化器，输出干净可读的单行格式

    格式: 2026-04-01 01:10:20 [INFO][main] Application started
    自动解析 structlog JSON 输出提取 event 字段，得到干净的单行日志
    """

    def format(self, record):
        msg = record.getMessage()

        # 尝试解析 structlog 输出的 JSON，提取 event 字段
        # 如果不是 JSON 格式（比如直接用标准 logging 输出），直接使用原始消息
        try:
            data = json.loads(msg)
            if isinstance(data, dict):
                event = data.get('event', msg)
                # 如果 event 本身包含换行（如多行JSON），压缩成一行
                if isinstance(event, str):
                    event = ' '.join(line.strip() for line in event.splitlines())
                msg = event
                # 如果有 enabled 字段，追加状态（开启/关闭）
                if 'enabled' in data:
                    enabled = data['enabled']
                    status = "开启" if enabled else "关闭"
                    msg = f"{msg} -> {status}"
        except (json.JSONDecodeError, TypeError):
            pass

        # 时间戳 + 级别 + logger名 + 事件消息
        # 格式: 2026-04-01 01:10:20 [INFO][main] Application started
        asctime = self.formatTime(record, self.datefmt)
        return f"{asctime} [{record.levelname}][{record.name}] {msg}"


def create_timed_file_handler(
    path: Path,
    level: int,
    backup_count: int = LOG_FULL_BACKUP_COUNT,
    log_filter: logging.Filter = None
) -> TimedRotatingFileHandler:
    """创建定时轮转文件处理器"""
    handler = TimedRotatingFileHandler(
        path,
        when=LOG_ROTATION_WHEN,
        interval=LOG_ROTATION_INTERVAL,
        backupCount=backup_count,
        encoding="utf-8"
    )
    handler.setLevel(level)
    if log_filter:
        handler.addFilter(log_filter)
    return handler


def setup_logging() -> None:
    """Set up structured logging configuration."""

    logs_dir = BASE_DIR.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Determine log level
    log_level = logging.DEBUG if settings.debug else logging.INFO

    # Configure structlog for standard library logging
    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        TimeStamper(fmt="iso"),
        JSONRenderer(indent=2 if settings.debug else None),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set up handlers
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processors=processors,
        )
    )
    handlers.append(console_handler)

    # Full logs handler - all DEBUG+ level in JSON format
    full_log_path = logs_dir / "log_full.log"
    full_handler = create_timed_file_handler(
        full_log_path,
        level=logging.DEBUG,
        backup_count=LOG_FULL_BACKUP_COUNT
    )
    full_handler.setFormatter(structlog.stdlib.ProcessorFormatter(processors=processors))
    handlers.append(full_handler)

    # Main logs handler - filtered INFO+ level in human-readable format
    main_log_path = logs_dir / "log_main.log"
    main_formatter = MainLogFormatter(
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    main_handler = create_timed_file_handler(
        main_log_path,
        level=logging.INFO,
        backup_count=LOG_MAIN_BACKUP_COUNT,
        log_filter=MainLogFilter()
    )
    main_handler.setFormatter(main_formatter)
    handlers.append(main_handler)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers and add new ones
    for existing_handler in root_logger.handlers:
        root_logger.removeHandler(existing_handler)
    for handler in handlers:
        root_logger.addHandler(handler)

    # Set higher log level for noisy third-party libraries
    logging.getLogger("websockets").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str = __name__):
    """Get a structured logger instance."""
    return structlog.get_logger(name)
