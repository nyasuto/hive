#!/usr/bin/env python3
"""
Mock helpers for conversation system testing
"""

import json
import subprocess
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch


class MockSubprocessHelper:
    """Helper for mocking subprocess calls"""

    def __init__(self):
        self.call_history: List[Dict[str, Any]] = []

    def mock_subprocess_run(self, cmd: List[str], **kwargs) -> Mock:
        """Mock subprocess.run with call tracking"""
        result = Mock()
        result.returncode = 0
        result.stdout = "Mock output"
        result.stderr = ""
        
        # Track the call
        self.call_history.append({
            'cmd': cmd,
            'kwargs': kwargs,
            'timestamp': datetime.now().isoformat()
        })
        
        return result

    def get_last_call(self) -> Dict[str, Any] | None:
        """Get the last subprocess call"""
        return self.call_history[-1] if self.call_history else None

    def get_calls_by_command(self, command: str) -> List[Dict[str, Any]]:
        """Get calls that contain specific command"""
        return [
            call for call in self.call_history
            if any(command in str(arg) for arg in call['cmd'])
        ]

    def clear_history(self) -> None:
        """Clear call history"""
        self.call_history.clear()


class MockTmuxHelper:
    """Helper for mocking tmux operations"""

    def __init__(self):
        self.sessions = {"test_beehive": True}
        self.panes = {
            "0": {"title": "queen", "active": True},
            "1": {"title": "developer", "active": True},
            "2": {"title": "qa", "active": True},
            "3": {"title": "analyst", "active": True}
        }
        self.sent_messages: List[Dict[str, Any]] = []

    def mock_has_session(self, session_name: str) -> bool:
        """Mock tmux has-session check"""
        return session_name in self.sessions

    def mock_list_panes(self, session_name: str) -> List[str]:
        """Mock tmux list-panes"""
        if session_name in self.sessions:
            return [pane["title"] for pane in self.panes.values()]
        return []

    def mock_send_keys(self, session: str, pane: str, message: str) -> None:
        """Mock tmux send-keys"""
        self.sent_messages.append({
            'session': session,
            'pane': pane,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    def get_sent_messages(self, pane: str | None = None) -> List[Dict[str, Any]]:
        """Get messages sent to specific pane or all"""
        if pane is None:
            return self.sent_messages
        return [msg for msg in self.sent_messages if msg['pane'] == pane]

    def clear_messages(self) -> None:
        """Clear sent messages history"""
        self.sent_messages.clear()


class MockFileSystemHelper:
    """Helper for mocking file system operations"""

    def __init__(self):
        self.files: Dict[str, str] = {}
        self.directories: List[str] = []

    def mock_path_exists(self, path: str) -> bool:
        """Mock Path.exists()"""
        return path in self.files or path in self.directories

    def mock_read_text(self, path: str) -> str:
        """Mock file reading"""
        return self.files.get(path, "")

    def mock_write_text(self, path: str, content: str) -> None:
        """Mock file writing"""
        self.files[path] = content

    def add_file(self, path: str, content: str = "") -> None:
        """Add a mock file"""
        self.files[path] = content

    def add_directory(self, path: str) -> None:
        """Add a mock directory"""
        self.directories.append(path)


class MockDateTimeHelper:
    """Helper for mocking datetime operations"""

    def __init__(self, fixed_time: datetime | None = None):
        self.fixed_time = fixed_time or datetime(2025, 1, 1, 12, 0, 0)
        self.call_count = 0

    def mock_now(self) -> datetime:
        """Mock datetime.now()"""
        self.call_count += 1
        return self.fixed_time

    def advance_time(self, **kwargs) -> None:
        """Advance the fixed time"""
        from datetime import timedelta
        self.fixed_time += timedelta(**kwargs)


class ConversationTestMocks:
    """Comprehensive mock setup for conversation system testing"""

    def __init__(self):
        self.subprocess_helper = MockSubprocessHelper()
        self.tmux_helper = MockTmuxHelper()
        self.filesystem_helper = MockFileSystemHelper()
        self.datetime_helper = MockDateTimeHelper()
        
        # Mock patches
        self.patches: List[Any] = []

    def __enter__(self):
        """Context manager entry"""
        # Patch subprocess
        subprocess_patch = patch('subprocess.run', side_effect=self.subprocess_helper.mock_subprocess_run)
        self.patches.append(subprocess_patch)
        subprocess_patch.start()

        # Patch datetime
        datetime_patch = patch('bees.conversation_logger.datetime')
        mock_datetime = datetime_patch.start()
        mock_datetime.now.return_value = self.datetime_helper.fixed_time
        self.patches.append(datetime_patch)

        datetime_patch2 = patch('bees.conversation_manager.datetime') 
        mock_datetime2 = datetime_patch2.start()
        mock_datetime2.now.return_value = self.datetime_helper.fixed_time
        self.patches.append(datetime_patch2)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        for patch_obj in self.patches:
            patch_obj.stop()
        self.patches.clear()

    def setup_successful_cli_send(self) -> None:
        """Setup successful CLI send scenario"""
        self.tmux_helper.sessions["test_beehive"] = True

    def setup_failed_cli_send(self) -> None:
        """Setup failed CLI send scenario"""
        def failing_subprocess(*args, **kwargs):
            result = Mock()
            result.returncode = 1
            result.stderr = "Command failed"
            error = subprocess.CalledProcessError(1, args[0])
            error.stderr = "Command failed"
            raise error

        # Replace the subprocess mock
        for patch_obj in self.patches:
            if hasattr(patch_obj, 'new') and 'subprocess' in str(patch_obj):
                patch_obj.stop()
                self.patches.remove(patch_obj)
                break

        failing_patch = patch('subprocess.run', side_effect=failing_subprocess)
        self.patches.append(failing_patch)
        failing_patch.start()

    def get_subprocess_calls(self) -> List[Dict[str, Any]]:
        """Get all subprocess calls"""
        return self.subprocess_helper.call_history

    def get_tmux_messages(self) -> List[Dict[str, Any]]:
        """Get all tmux messages"""
        return self.tmux_helper.sent_messages