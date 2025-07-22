#!/usr/bin/env python3
"""
Test module for configuration system
Testing configuration validation, loading, and error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from bees.config import (
    BeehiveConfig,
    get_config,
)
from bees.exceptions import ConfigurationError, ConfigurationLoadError, ConfigurationValidationError


class TestBeehiveConfig:
    """Test BeehiveConfig dataclass"""

    def test_default_configuration(self):
        """Test default configuration values"""
        config = BeehiveConfig()

        # Check default values
        assert config.hive_db_path == "hive/hive_memory.db"
        assert config.session_name == "beehive"
        assert config.heartbeat_interval == 5.0
        assert config.log_level == "INFO"
        assert config.structured_logging is True
        assert config.db_timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

        # Check pane mapping
        assert "queen" in config.pane_mapping
        assert "developer" in config.pane_mapping
        assert "qa" in config.pane_mapping

    def test_custom_configuration(self):
        """Test configuration with custom values"""
        custom_pane_mapping = {
            "queen": "custom_queen",
            "developer": "custom_dev",
            "qa": "custom_qa",
        }
        custom_pane_id_mapping = {"queen": "beehive:0", "developer": "beehive:1", "qa": "beehive:2"}

        config = BeehiveConfig(
            hive_db_path="custom/path.db",
            session_name="custom_session",
            heartbeat_interval=10.0,
            log_level="DEBUG",
            structured_logging=False,
            pane_mapping=custom_pane_mapping,
            pane_id_mapping=custom_pane_id_mapping,
        )

        assert config.hive_db_path == "custom/path.db"
        assert config.session_name == "custom_session"
        assert config.heartbeat_interval == 10.0
        assert config.log_level == "DEBUG"
        assert config.structured_logging is False
        assert config.pane_mapping == custom_pane_mapping

    def test_validate_method_success(self):
        """Test successful validation"""
        config = BeehiveConfig()
        # Should not raise any exception
        config.validate()

    def test_validate_invalid_log_level(self):
        """Test validation with invalid log level"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(log_level="INVALID")

        assert "log_level" in str(exc_info.value)
        assert "INVALID" in str(exc_info.value)

    def test_validate_negative_heartbeat_interval(self):
        """Test validation with negative heartbeat interval"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(heartbeat_interval=-1.0)

        assert "heartbeat_interval" in str(exc_info.value)
        assert "positive" in str(exc_info.value)

    def test_validate_negative_db_timeout(self):
        """Test validation with negative database timeout"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(db_timeout=-5.0)

        assert "db_timeout" in str(exc_info.value)

    def test_validate_negative_max_retries(self):
        """Test validation with negative max retries"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(max_retries=-1)

        assert "max_retries" in str(exc_info.value)

    def test_validate_empty_pane_mapping(self):
        """Test validation with empty pane mapping"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(pane_mapping={})

        assert "pane_mapping" in str(exc_info.value)
        assert "Missing pane mapping for bee" in str(exc_info.value)

    def test_validate_missing_required_panes(self):
        """Test validation with missing required panes"""
        with pytest.raises(ConfigurationValidationError) as exc_info:
            BeehiveConfig(pane_mapping={"custom": 1})

        assert "queen" in str(exc_info.value) or "developer" in str(exc_info.value)

    def test_to_dict_method(self):
        """Test to_dict method"""
        config = BeehiveConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["hive_db_path"] == config.hive_db_path
        assert config_dict["session_name"] == config.session_name
        assert config_dict["log_level"] == config.log_level

    def test_from_dict_method(self):
        """Test from_dict method"""
        config_data = {
            "hive_db_path": "test.db",
            "session_name": "test_session",
            "log_level": "DEBUG",
            "heartbeat_interval": 15.0,
        }

        config = BeehiveConfig.from_dict(config_data)

        assert config.hive_db_path == "test.db"
        assert config.session_name == "test_session"
        assert config.log_level == "DEBUG"
        assert config.heartbeat_interval == 15.0

    def test_from_dict_with_invalid_data(self):
        """Test from_dict with invalid data"""
        config_data = {"hive_db_path": "test.db", "invalid_field": "should_be_ignored"}

        config = BeehiveConfig.from_dict(config_data)
        assert config.hive_db_path == "test.db"
        # Invalid field should be ignored, defaults should be used
        assert config.session_name == "beehive"  # default value


class TestConfigurationLoading:
    """Test configuration loading functions"""

    def test_get_config_default(self):
        """Test get_config returns default configuration"""
        config = get_config()
        assert isinstance(config, BeehiveConfig)
        assert config.session_name == "beehive"  # default value

    @patch.dict("os.environ", {}, clear=True)
    def test_get_config_no_env(self):
        """Test get_config with no environment variables"""
        config = get_config()
        assert isinstance(config, BeehiveConfig)
        assert config.log_level == "INFO"  # default value

    def test_load_config_from_file_success(self):
        """Test successful config loading from file"""
        config_data = {
            "hive_db_path": "test.db",
            "session_name": "test_session",
            "log_level": "DEBUG",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            config = BeehiveConfig.from_file(temp_file)
            assert config.hive_db_path == "test.db"
            assert config.session_name == "test_session"
            assert config.log_level == "DEBUG"
        finally:
            Path(temp_file).unlink()

    def test_load_config_from_nonexistent_file(self):
        """Test loading config from nonexistent file"""
        with pytest.raises(ConfigurationLoadError) as exc_info:
            BeehiveConfig.from_file("nonexistent_file.json")

        assert "nonexistent_file.json" in str(exc_info.value)

    def test_load_config_from_invalid_json(self):
        """Test loading config from invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_file = f.name

        try:
            with pytest.raises(ConfigurationLoadError) as exc_info:
                BeehiveConfig.from_file(temp_file)

            assert "JSON" in str(exc_info.value)
        finally:
            Path(temp_file).unlink()

    def test_load_config_from_env_with_values(self):
        """Test loading config from environment variables"""
        env_vars = {
            "BEEHIVE_DB_PATH": "env_test.db",
            "BEEHIVE_SESSION_NAME": "env_session",
            "BEEHIVE_LOG_LEVEL": "ERROR",
            "BEEHIVE_HEARTBEAT_INTERVAL": "20.0",
            "BEEHIVE_STRUCTURED_LOGGING": "false",
        }

        with patch.dict("os.environ", env_vars):
            config = BeehiveConfig.from_env()

            assert config.hive_db_path == "env_test.db"
            assert config.session_name == "env_session"
            assert config.log_level == "ERROR"
            assert config.heartbeat_interval == 20.0
            assert config.structured_logging is False

    def test_load_config_from_env_with_invalid_values(self):
        """Test loading config from environment with invalid values"""
        env_vars = {
            "BEEHIVE_HEARTBEAT_INTERVAL": "not_a_number",
            "BEEHIVE_STRUCTURED_LOGGING": "not_a_boolean",
        }

        with patch.dict("os.environ", env_vars):
            with pytest.raises(ConfigurationValidationError) as exc_info:
                BeehiveConfig.from_env()

            # Should mention the invalid value
            assert "BEEHIVE_HEARTBEAT_INTERVAL" in str(exc_info.value)

    @patch.dict("os.environ", {}, clear=True)
    def test_load_config_from_env_empty(self):
        """Test loading config from environment with no variables set"""
        config = BeehiveConfig.from_env()
        # Should return default values
        assert config.hive_db_path == "hive/hive_memory.db"
        assert config.session_name == "beehive"


class TestConfigurationIntegration:
    """Integration tests for configuration system"""

    def test_configuration_precedence(self):
        """Test configuration precedence: env vars override defaults"""
        env_vars = {"BEEHIVE_LOG_LEVEL": "DEBUG"}

        with patch.dict("os.environ", env_vars):
            config = get_config()
            assert config.log_level == "DEBUG"

    def test_invalid_configuration_raises_error(self):
        """Test that invalid configuration raises error during validation"""
        env_vars = {"BEEHIVE_LOG_LEVEL": "INVALID_LEVEL"}

        with patch.dict("os.environ", env_vars):
            with pytest.raises(ConfigurationError):
                get_config()

    def test_configuration_validation_in_get_config(self):
        """Test that get_config validates configuration"""
        env_vars = {"BEEHIVE_HEARTBEAT_INTERVAL": "-1.0"}

        with patch.dict("os.environ", env_vars):
            with pytest.raises(ConfigurationValidationError) as exc_info:
                BeehiveConfig.from_env()

            assert "heartbeat_interval" in str(exc_info.value)

    def test_file_config_overrides_env_config(self):
        """Test that file configuration can override environment configuration"""
        env_vars = {"BEEHIVE_LOG_LEVEL": "DEBUG"}

        config_data = {"log_level": "ERROR"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            with patch.dict("os.environ", env_vars):
                file_config = BeehiveConfig.from_file(temp_file)
                env_config = BeehiveConfig.from_env()

                assert file_config.log_level == "ERROR"
                assert env_config.log_level == "DEBUG"
        finally:
            Path(temp_file).unlink()

    @pytest.mark.mock_required
    def test_configuration_error_handling(self):
        """Test error handling during configuration loading"""
        with patch("bees.config.open", mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")

            with pytest.raises(ConfigurationLoadError) as exc_info:
                BeehiveConfig.from_file("test.json")

            assert "Permission denied" in str(exc_info.value)
