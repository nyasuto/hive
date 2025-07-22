"""
Beehive Custom Exceptions
Issue #22: コード品質・エラーハンドリング強化

Beehiveシステム内で使用するカスタム例外クラス群
"""

from typing import Any


class BeehiveError(Exception):
    """
    Beehive システム基底例外

    全てのBeehive関連例外の基底クラス。
    エラーコードとメタデータを持つことができる。
    """

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.metadata = metadata or {}

    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.error_code:
            return f"[{self.error_code}] {base_msg}"
        return base_msg

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary representation"""
        return {
            "error_type": self.__class__.__name__,
            "message": str(self),
            "error_code": self.error_code,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert exception to JSON representation"""
        import json

        return json.dumps(self.to_dict())


class DatabaseError(BeehiveError):
    """データベース関連エラーの基底クラス"""

    pass


class DatabaseConnectionError(DatabaseError):
    """
    データベース接続エラー

    SQLiteデータベースへの接続に失敗した場合に発生
    """

    def __init__(self, db_path: str, original_error: Exception | None = None):
        message = f"Failed to connect to database: {db_path}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "db_path": db_path,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="DB_CONNECTION_FAILED", metadata=metadata)
        self.db_path = db_path
        self.original_error = original_error


class DatabaseOperationError(DatabaseError):
    """
    データベース操作エラー

    SQLクエリ実行時のエラー
    """

    def __init__(self, operation: str, query: str, original_error: Exception | None = None):
        message = f"Database operation failed: {operation}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "operation": operation,
            "query": query,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="DB_OPERATION_FAILED", metadata=metadata)
        self.operation = operation
        self.query = query
        self.original_error = original_error


class CommunicationError(BeehiveError):
    """通信関連エラーの基底クラス"""

    pass


class TmuxSessionError(CommunicationError):
    """
    tmuxセッション関連エラー

    tmuxセッションが見つからない、または操作に失敗した場合
    """

    def __init__(self, session_name: str, operation: str, original_error: Exception | None = None):
        message = f"tmux session operation failed: {operation} on session '{session_name}'"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "session_name": session_name,
            "operation": operation,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="TMUX_SESSION_ERROR", metadata=metadata)
        self.session_name = session_name
        self.operation = operation
        self.original_error = original_error


class TmuxCommandError(CommunicationError):
    """
    tmuxコマンド実行エラー

    tmuxコマンドの実行に失敗した場合
    """

    def __init__(self, command: str, original_error: Exception | None = None):
        message = f"tmux command execution failed: {command}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "command": command,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="TMUX_COMMAND_FAILED", metadata=metadata)
        self.command = command
        self.original_error = original_error


class MessageSendError(CommunicationError):
    """
    メッセージ送信エラー

    Bee間のメッセージ送信に失敗した場合
    """

    def __init__(
        self,
        from_bee: str,
        to_bee: str,
        message_type: str,
        original_error: Exception | None = None,
    ):
        message = f"Failed to send {message_type} message from {from_bee} to {to_bee}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "from_bee": from_bee,
            "to_bee": to_bee,
            "message_type": message_type,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="MESSAGE_SEND_FAILED", metadata=metadata)
        self.from_bee = from_bee
        self.to_bee = to_bee
        self.message_type = message_type
        self.original_error = original_error


class ValidationError(BeehiveError):
    """入力検証関連エラーの基底クラス"""

    pass


class BeeNotFoundError(ValidationError):
    """
    Bee検索エラー

    指定されたBeeが見つからない場合
    """

    def __init__(self, bee_name: str, available_bees: list[str] | None = None):
        message = f"Bee not found: {bee_name}"
        if available_bees:
            message += f" (Available bees: {', '.join(available_bees)})"

        metadata = {
            "bee_name": bee_name,
            "available_bees": available_bees or [],
        }

        super().__init__(message, error_code="BEE_NOT_FOUND", metadata=metadata)
        self.bee_name = bee_name
        self.available_bees = available_bees or []


class TaskValidationError(ValidationError):
    """
    タスク検証エラー

    タスクID、タスクデータの検証に失敗した場合
    """

    def __init__(self, field: str, value: Any, reason: str):
        message = f"Task validation failed: {field}={value} ({reason})"

        metadata = {"field": field, "value": str(value), "reason": reason}

        super().__init__(message, error_code="TASK_VALIDATION_FAILED", metadata=metadata)
        self.field = field
        self.value = value
        self.reason = reason


class BeeValidationError(ValidationError):
    """
    Bee検証エラー

    Bee名、状態の検証に失敗した場合
    """

    def __init__(self, bee_name: str, field: str, value: Any, reason: str):
        message = f"Bee validation failed: {bee_name}.{field}={value} ({reason})"

        metadata = {"bee_name": bee_name, "field": field, "value": str(value), "reason": reason}

        super().__init__(message, error_code="BEE_VALIDATION_FAILED", metadata=metadata)
        self.bee_name = bee_name
        self.field = field
        self.value = value
        self.reason = reason


class ConfigurationError(BeehiveError):
    """設定関連エラーの基底クラス"""

    pass


class ConfigurationLoadError(ConfigurationError):
    """
    設定読み込みエラー

    設定ファイルの読み込みに失敗した場合
    """

    def __init__(self, config_path: str, original_error: Exception | None = None):
        message = f"Failed to load configuration from: {config_path}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "config_path": config_path,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="CONFIG_LOAD_FAILED", metadata=metadata)
        self.config_path = config_path
        self.original_error = original_error


class ConfigurationValidationError(ConfigurationError):
    """
    設定検証エラー

    設定値の検証に失敗した場合
    """

    def __init__(self, key: str, value: Any, reason: str):
        message = f"Configuration validation failed: {key}={value} ({reason})"

        metadata = {"key": key, "value": str(value), "reason": reason}

        super().__init__(message, error_code="CONFIG_VALIDATION_FAILED", metadata=metadata)
        self.key = key
        self.value = value
        self.reason = reason


class WorkflowError(BeehiveError):
    """ワークフロー実行関連エラーの基底クラス"""

    pass


class TaskExecutionError(WorkflowError):
    """
    タスク実行エラー

    タスクの実行中にエラーが発生した場合
    """

    def __init__(
        self, task_id: int, bee_name: str, stage: str, original_error: Exception | None = None
    ):
        message = f"Task execution failed: Task#{task_id} at {stage} by {bee_name}"
        if original_error:
            message += f" (Cause: {original_error})"

        metadata = {
            "task_id": task_id,
            "bee_name": bee_name,
            "stage": stage,
            "original_error": str(original_error) if original_error else None,
        }

        super().__init__(message, error_code="TASK_EXECUTION_FAILED", metadata=metadata)
        self.task_id = task_id
        self.bee_name = bee_name
        self.stage = stage
        self.original_error = original_error


class WorkflowStateError(WorkflowError):
    """
    ワークフロー状態エラー

    ワークフローの状態遷移が不正な場合
    """

    def __init__(self, current_state: str, attempted_operation: str, reason: str):
        message = f"Invalid workflow state transition: {attempted_operation} from {current_state} ({reason})"

        metadata = {
            "current_state": current_state,
            "attempted_operation": attempted_operation,
            "reason": reason,
        }

        super().__init__(message, error_code="WORKFLOW_STATE_ERROR", metadata=metadata)
        self.current_state = current_state
        self.attempted_operation = attempted_operation
        self.reason = reason


# 便利なユーティリティ関数とデコレータ
def error_handler(func):
    """
    汎用エラーハンドリングデコレータ

    BeehiveErrorは再発生、その他の例外はBeehiveErrorでラップ

    Usage:
        @error_handler
        def some_operation(self):
            # 何らかの処理
            pass
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BeehiveError:
            # BeehiveError系はそのまま再発生
            raise
        except Exception as e:
            # その他の例外はBeehiveErrorでラップ
            raise BeehiveError(
                message=f"Unexpected error in {func.__name__}: {e}",
                error_code="UNEXPECTED_ERROR",
                metadata={
                    "function": func.__name__,
                    "original_error_type": e.__class__.__name__,
                    "original_error_message": str(e),
                },
            ) from e

    return wrapper


def wrap_database_error(func):
    """
    データベース操作をラップしてカスタム例外に変換するデコレータ

    Usage:
        @wrap_database_error
        def some_db_operation(self):
            # データベース操作
            pass
    """
    import functools
    import sqlite3

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            # SQLite例外はDatabaseOperationErrorに変換
            raise DatabaseOperationError(
                operation=func.__name__, query="Unknown", original_error=e
            ) from e
        except Exception:
            # その他の例外はそのまま再発生
            raise

    return wrapper


def wrap_communication_error(func):
    """
    通信操作をラップしてカスタム例外に変換するデコレータ

    Usage:
        @wrap_communication_error
        def send_message(self, ...):
            # 通信処理
            pass
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "tmux" in str(e).lower():
                raise TmuxSessionError(
                    session_name="beehive", operation=func.__name__, original_error=e
                )
            else:
                raise MessageSendError(
                    from_bee=(
                        args[0].bee_name if args and hasattr(args[0], "bee_name") else "unknown"
                    ),
                    to_bee=args[1] if len(args) > 1 else "unknown",
                    message_type=func.__name__,
                    original_error=e,
                )

    return wrapper
