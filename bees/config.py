"""
Beehive Configuration Management
Issue #22: コード品質・エラーハンドリング強化

設定の外部化とバリデーションを提供
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationLoadError, ConfigurationValidationError


@dataclass
class BeehiveConfig:
    """
    Beehive システム設定クラス

    全ての設定項目を一元管理し、デフォルト値とバリデーションを提供
    """

    # データベース設定
    hive_db_path: str = "hive/hive_memory.db"
    db_path: str = "hive/hive_memory.db"  # CLI用のエイリアス
    db_timeout: float = 30.0
    db_backup_enabled: bool = True
    db_backup_interval: int = 3600  # seconds

    # tmux設定
    session_name: str = "beehive"
    # bee名前をそのまま使用（より直感的）
    pane_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "queen": "queen",
            "developer": "developer",
            "qa": "qa",
            "analyst": "analyst",
        }
    )
    # ペインIDマッピング（bee名 -> tmuxウィンドウID）
    pane_id_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "queen": "beehive:0",
            "developer": "beehive:1",
            "qa": "beehive:2",
            "analyst": "beehive:3",
        }
    )

    # 通信設定
    heartbeat_interval: float = 5.0
    message_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds

    # ログ設定
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file_enabled: bool = True
    log_file_path: str = "logs/beehive.log"
    structured_logging: bool = True

    # パフォーマンス設定
    task_processing_batch_size: int = 10
    concurrent_tasks_limit: int = 5
    memory_cleanup_interval: int = 1800  # seconds

    # Queen Bee設定
    available_bees: list[str] = field(default_factory=lambda: ["developer", "qa", "analyst"])
    task_assignment_strategy: str = "balanced"  # balanced, priority, workload
    max_tasks_per_bee: int = 3

    # 品質・監視設定
    quality_gate_coverage_min: float = 85.0
    performance_benchmark_enabled: bool = True
    metrics_collection_enabled: bool = True

    # 開発・デバッグ設定
    debug_mode: bool = False
    verbose_logging: bool = False
    mock_tmux: bool = False  # テスト用

    def __post_init__(self):
        """設定値のバリデーション"""
        self.validate()

    def validate(self) -> None:
        """
        設定値の妥当性をチェック

        Raises:
            ConfigurationValidationError: 設定値が不正な場合
        """
        validators = [
            ("hive_db_path", self.hive_db_path, self._validate_db_path),
            ("session_name", self.session_name, self._validate_session_name),
            ("heartbeat_interval", self.heartbeat_interval, self._validate_positive_float),
            ("db_timeout", self.db_timeout, self._validate_positive_float),
            ("message_timeout", self.message_timeout, self._validate_positive_int),
            ("max_retries", self.max_retries, self._validate_positive_int),
            ("log_level", self.log_level, self._validate_log_level),
            (
                "quality_gate_coverage_min",
                self.quality_gate_coverage_min,
                self._validate_percentage,
            ),
            ("pane_mapping", self.pane_mapping, self._validate_pane_mapping),
            ("pane_id_mapping", self.pane_id_mapping, self._validate_pane_id_mapping),
        ]

        for key, value, validator in validators:
            try:
                validator(value)
            except ValueError as e:
                raise ConfigurationValidationError(key, value, str(e))

    def _validate_db_path(self, value: str) -> None:
        """データベースパスの検証"""
        if not value or not isinstance(value, str):
            raise ValueError("Database path must be a non-empty string")

        # 親ディレクトリの存在確認
        db_path = Path(value)
        if not db_path.parent.exists():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create database directory: {e}")

    def _validate_session_name(self, value: str) -> None:
        """tmuxセッション名の検証"""
        if not value or not isinstance(value, str):
            raise ValueError("Session name must be a non-empty string")

        if len(value) > 50:
            raise ValueError("Session name must be 50 characters or less")

        # tmuxで使用できない文字をチェック
        invalid_chars = [" ", "\t", "\n", ":", "."]
        for char in invalid_chars:
            if char in value:
                raise ValueError(f"Session name contains invalid character: '{char}'")

    def _validate_positive_float(self, value: float) -> None:
        """正の浮動小数点数の検証"""
        if not isinstance(value, int | float) or value <= 0:
            raise ValueError("Value must be a positive number")

    def _validate_positive_int(self, value: int) -> None:
        """正の整数の検証"""
        if not isinstance(value, int) or value <= 0:
            raise ValueError("Value must be a positive integer")

    def _validate_log_level(self, value: str) -> None:
        """ログレベルの検証"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if value not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")

    def _validate_percentage(self, value: float) -> None:
        """パーセンテージ値の検証"""
        if not isinstance(value, int | float) or not (0 <= value <= 100):
            raise ValueError("Value must be between 0 and 100")

    def _validate_pane_mapping(self, value: dict[str, str]) -> None:
        """ペインマッピングの検証"""
        if not isinstance(value, dict):
            raise ValueError("Pane mapping must be a dictionary")

        required_bees = ["queen", "developer", "qa", "analyst"]
        for bee in required_bees:
            if bee not in value:
                raise ValueError(f"Missing pane mapping for bee: {bee}")

        # ペイン名の検証
        for bee, pane_name in value.items():
            if not isinstance(pane_name, str) or not pane_name:
                raise ValueError(f"Invalid pane name for {bee}: {pane_name}")

    def _validate_pane_id_mapping(self, value: dict[str, str]) -> None:
        """ペインIDマッピングの検証"""
        if not isinstance(value, dict):
            raise ValueError("Pane ID mapping must be a dictionary")

        required_bees = ["queen", "developer", "qa", "analyst"]
        for bee in required_bees:
            if bee not in value:
                raise ValueError(f"Missing pane ID mapping for bee: {bee}")

        # ウィンドウID形式の検証 (session:N 形式)
        for bee, pane_id in value.items():
            if not isinstance(pane_id, str) or not pane_id:
                raise ValueError(f"Invalid pane ID for {bee}: {pane_id}")
            # session:N形式をサポート
            if ":" not in pane_id:
                raise ValueError(
                    f"Invalid window ID format for {bee}: {pane_id} (expected format: session:N)"
                )
            session_part, window_part = pane_id.split(":", 1)
            if not session_part or not window_part.isdigit():
                raise ValueError(
                    f"Invalid window ID format for {bee}: {pane_id} (expected format: session:N)"
                )

    @classmethod
    def from_file(cls, config_path: str | Path) -> "BeehiveConfig":
        """
        設定ファイルから設定をロード

        Args:
            config_path: 設定ファイルのパス (.json)

        Returns:
            BeehiveConfig: 設定オブジェクト

        Raises:
            ConfigurationLoadError: ファイル読み込みに失敗した場合
        """
        config_path = Path(config_path)

        try:
            if not config_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")

            with open(config_path, encoding="utf-8") as f:
                config_data = json.load(f)

            return cls(**config_data)

        except (FileNotFoundError, json.JSONDecodeError, TypeError) as e:
            raise ConfigurationLoadError(str(config_path), e)

    @classmethod
    def from_env(cls, prefix: str = "BEEHIVE_") -> "BeehiveConfig":
        """
        環境変数から設定をロード

        Args:
            prefix: 環境変数のプレフィックス

        Returns:
            BeehiveConfig: 設定オブジェクト
        """
        config_data = {}

        # 環境変数マッピング
        env_mapping = {
            f"{prefix}DB_PATH": "hive_db_path",
            f"{prefix}SESSION_NAME": "session_name",
            f"{prefix}HEARTBEAT_INTERVAL": "heartbeat_interval",
            f"{prefix}LOG_LEVEL": "log_level",
            f"{prefix}DEBUG_MODE": "debug_mode",
            f"{prefix}MOCK_TMUX": "mock_tmux",
        }

        for env_key, config_key in env_mapping.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                # 型変換
                if config_key in ["heartbeat_interval", "quality_gate_coverage_min"]:
                    config_data[config_key] = float(env_value)
                elif config_key in ["message_timeout", "max_retries", "task_processing_batch_size"]:
                    config_data[config_key] = int(env_value)
                elif config_key in ["debug_mode", "verbose_logging", "mock_tmux"]:
                    config_data[config_key] = env_value.lower() in ("true", "1", "yes")
                else:
                    config_data[config_key] = env_value

        return cls(**config_data)

    def to_file(self, config_path: str | Path) -> None:
        """
        設定をファイルに保存

        Args:
            config_path: 設定ファイルのパス (.json)

        Raises:
            ConfigurationLoadError: ファイル書き込みに失敗した場合
        """
        config_path = Path(config_path)

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            config_dict = {
                key: value for key, value in self.__dict__.items() if not key.startswith("_")
            }

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

        except (OSError, TypeError) as e:
            raise ConfigurationLoadError(str(config_path), e)

    def get_database_url(self) -> str:
        """データベースURLを取得"""
        return f"sqlite:///{self.hive_db_path}"

    def get_log_config(self) -> dict[str, Any]:
        """ログ設定を辞書形式で取得"""
        return {
            "level": self.log_level,
            "format": self.log_format,
            "file_enabled": self.log_file_enabled,
            "file_path": self.log_file_path,
            "structured": self.structured_logging,
        }

    def is_development_mode(self) -> bool:
        """開発モードかどうかを判定"""
        return self.debug_mode or self.verbose_logging

    def to_dict(self) -> dict[str, Any]:
        """設定を辞書形式で取得"""
        return {key: value for key, value in self.__dict__.items() if not key.startswith("_")}

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "BeehiveConfig":
        """辞書から設定オブジェクトを作成"""
        return cls(**config_dict)

    def __str__(self) -> str:
        """設定内容を文字列で表現（機密情報は隠す）"""
        safe_config = {}
        for key, value in self.__dict__.items():
            if "password" in key.lower() or "secret" in key.lower():
                safe_config[key] = "***"
            else:
                safe_config[key] = value

        return f"BeehiveConfig({safe_config})"


# グローバル設定インスタンス（シングルトンパターン）
_config_instance: BeehiveConfig | None = None


def get_config() -> BeehiveConfig:
    """
    グローバル設定インスタンスを取得

    Returns:
        BeehiveConfig: グローバル設定インスタンス
    """
    global _config_instance

    if _config_instance is None:
        # 設定ファイルの優先順位
        config_paths = [
            "config/beehive.json",
            "beehive.json",
            os.path.expanduser("~/.beehive/config.json"),
        ]

        # 設定ファイルからロードを試行
        for config_path in config_paths:
            if Path(config_path).exists():
                try:
                    _config_instance = BeehiveConfig.from_file(config_path)
                    break
                except ConfigurationLoadError:
                    continue

        # 設定ファイルが見つからない場合は環境変数から
        if _config_instance is None:
            _config_instance = BeehiveConfig.from_env()

    return _config_instance


def set_config(config: BeehiveConfig) -> None:
    """
    グローバル設定インスタンスを設定（テスト用）

    Args:
        config: 設定オブジェクト
    """
    global _config_instance
    _config_instance = config
