"""
Beehive Structured Logging
Issue #22: コード品質・エラーハンドリング強化

構造化ログとログ管理機能を提供
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import BeehiveConfig, get_config
from .exceptions import BeehiveError


class StructuredFormatter(logging.Formatter):
    """
    構造化ログフォーマッター

    ログをJSON形式で出力し、検索・分析しやすくする
    """

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        # 基本ログデータ
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 例外情報があれば追加
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Beehive例外の詳細情報
        if hasattr(record, "beehive_error") and isinstance(record.beehive_error, BeehiveError):
            error = record.beehive_error
            log_data["beehive_error"] = {"error_code": error.error_code, "metadata": error.metadata}

        # 追加属性があれば含める
        if self.include_extra:
            extra_data = {}
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "beehive_error",
                ]:
                    extra_data[key] = value

            if extra_data:
                log_data["extra"] = extra_data

        return json.dumps(log_data, ensure_ascii=False, default=str)


class BeehiveLogger:
    """
    Beehive用ログ管理クラス

    構造化ログ、コンテキスト情報の自動付加、エラー追跡などを提供
    """

    def __init__(self, name: str, config: BeehiveConfig | None = None):
        self.name = name
        self.config = config or get_config()

        # ベースロガーの設定
        self.logger = logging.getLogger(f"beehive.{name}")
        self.logger.setLevel(getattr(logging, self.config.log_level))

        # ハンドラーがまだ設定されていない場合のみ設定
        if not self.logger.handlers:
            self._setup_handlers()

        # Bee固有のコンテキスト情報
        self.context = {
            "bee_name": name,
            "session_name": self.config.session_name,
            "pid": sys.modules["os"].getpid(),
        }

    def _setup_handlers(self) -> None:
        """ログハンドラーの設定"""

        # コンソール出力
        console_handler = logging.StreamHandler(sys.stdout)
        if self.config.structured_logging:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(self.config.log_format))
        self.logger.addHandler(console_handler)

        # ファイル出力
        if self.config.log_file_enabled:
            log_path = Path(self.config.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # ローテーション付きファイルハンドラー
            file_handler = logging.handlers.RotatingFileHandler(
                log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
            )

            if self.config.structured_logging:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(self.config.log_format))

            self.logger.addHandler(file_handler)

    def _log_with_context(
        self,
        level: int,
        message: str,
        extra: dict[str, Any] | None = None,
        task_id: int | None = None,
        operation: str | None = None,
        error: Exception | None = None,
    ) -> None:
        """コンテキスト情報付きでログを出力"""

        # 追加情報を統合
        log_extra = self.context.copy()
        if extra:
            log_extra.update(extra)

        if task_id is not None:
            log_extra["task_id"] = task_id

        if operation:
            log_extra["operation"] = operation

        if error:
            log_extra["beehive_error"] = error

        self.logger.log(level, message, extra=log_extra, exc_info=error is not None)

    def debug(self, message: str, **kwargs) -> None:
        """デバッグログ"""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """情報ログ"""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """警告ログ"""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """エラーログ"""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """クリティカルログ"""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def log_event(self, event_type: str, message: str, level: str = "INFO", **kwargs) -> None:
        """
        イベントログ（構造化）

        Args:
            event_type: イベントタイプ（task_created, message_sent等）
            message: メッセージ
            level: ログレベル
            **kwargs: 追加のコンテキスト情報
        """
        log_level = getattr(logging, level.upper(), logging.INFO)

        extra = kwargs.copy()
        extra["event_type"] = event_type

        self._log_with_context(log_level, message, extra=extra)

    def log_task_event(self, task_id: int, event_type: str, message: str, **kwargs) -> None:
        """タスク関連イベントログ"""
        self.log_event(event_type=f"task.{event_type}", message=message, task_id=task_id, **kwargs)

    def log_communication_event(
        self, from_bee: str, to_bee: str, message_type: str, success: bool, **kwargs
    ) -> None:
        """通信関連イベントログ"""
        self.log_event(
            event_type="communication.message_sent" if success else "communication.message_failed",
            message=f"Message {message_type}: {from_bee} -> {to_bee}",
            from_bee=from_bee,
            to_bee=to_bee,
            message_type=message_type,
            success=success,
            level="INFO" if success else "ERROR",
            **kwargs,
        )

    def log_performance_event(
        self, operation: str, duration_ms: float, success: bool = True, **kwargs
    ) -> None:
        """パフォーマンス関連イベントログ"""
        self.log_event(
            event_type="performance.operation",
            message=f"Operation {operation} took {duration_ms:.2f}ms",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            **kwargs,
        )

    def log_database_event(
        self, operation: str, table: str, affected_rows: int | None = None, **kwargs
    ) -> None:
        """データベース関連イベントログ"""
        message = f"Database {operation} on {table}"
        if affected_rows is not None:
            message += f" ({affected_rows} rows)"

        self.log_event(
            event_type="database.operation",
            message=message,
            db_operation=operation,
            db_table=table,
            affected_rows=affected_rows,
            **kwargs,
        )

    def set_context(self, **context) -> None:
        """ログコンテキストを設定"""
        self.context.update(context)

    def clear_context(self) -> None:
        """ログコンテキストをクリア（基本情報は残す）"""
        base_context = {
            "bee_name": self.name,
            "session_name": self.config.session_name,
            "pid": sys.modules["os"].getpid(),
        }
        self.context = base_context


# グローバルロガーインスタンス管理
_loggers: dict[str, BeehiveLogger] = {}


def get_logger(name: str, config: BeehiveConfig | None = None) -> BeehiveLogger:
    """
    Beehiveロガーインスタンスを取得（シングルトンパターン）

    Args:
        name: ロガー名（通常はBee名）
        config: 設定オブジェクト（省略時はデフォルト設定）

    Returns:
        BeehiveLogger: ロガーインスタンス
    """
    if name not in _loggers:
        _loggers[name] = BeehiveLogger(name, config)
    return _loggers[name]


def setup_logging(config: BeehiveConfig | None = None) -> None:
    """
    ログ設定を初期化

    Args:
        config: 設定オブジェクト
    """
    if config is None:
        config = get_config()

    # rootロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))

    # ログディレクトリの作成
    if config.log_file_enabled:
        log_path = Path(config.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)


def cleanup_logging() -> None:
    """ログリソースのクリーンアップ"""
    global _loggers

    for logger in _loggers.values():
        for handler in logger.logger.handlers:
            handler.close()

    _loggers.clear()
