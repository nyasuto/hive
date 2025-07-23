#!/usr/bin/env python3
"""
Conversation Daemon - 会話ログ管理デーモン
beekeeperとbeeの会話を監視・記録し、sender CLI使用を強制するデーモンプロセス
"""

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from bees.config import get_config
from bees.conversation_manager import ConversationManager
from bees.logging_config import get_logger


class ConversationDaemon:
    """会話管理デーモン"""

    def __init__(self, config_path: str | None = None):
        self.config = get_config()
        self.logger = get_logger("conversation_daemon", self.config)
        self.conversation_manager = ConversationManager(self.config)
        
        self.running = False
        self._setup_signal_handlers()
        
        self.logger.info("ConversationDaemon initialized")

    def _setup_signal_handlers(self) -> None:
        """シグナルハンドラーを設定"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def start(self, monitor_interval: float = 2.0) -> None:
        """デーモンを開始
        
        Args:
            monitor_interval: 監視間隔（秒）
        """
        self.running = True
        self.logger.info(f"Starting conversation daemon (interval: {monitor_interval}s)")
        
        try:
            while self.running:
                # 会話監視の実行
                self._monitor_conversations()
                
                # sender CLI違反チェック
                self._check_sender_cli_violations()
                
                # 定期統計レポート
                self._periodic_stats_report()
                
                time.sleep(monitor_interval)
                
        except Exception as e:
            self.logger.error(f"Critical error in conversation daemon: {e}")
            raise
        finally:
            self._cleanup()

    def stop(self) -> None:
        """デーモンを停止"""
        self.running = False
        self.logger.info("Conversation daemon stopping...")

    def intercept_beekeeper_command(self, command: str, target_bee: str = "all") -> bool:
        """beekeeperコマンドを傍受
        
        Args:
            command: beekeeperコマンド
            target_bee: 対象bee
            
        Returns:
            bool: 処理成功フラグ
        """
        return self.conversation_manager.intercept_beekeeper_input(command, target_bee)

    def _monitor_conversations(self) -> None:
        """会話を監視"""
        try:
            # 最近の会話をチェック
            recent_conversations = self.conversation_manager.conversation_logger.get_conversation_history(
                limit=10,
                include_beekeeper=True
            )
            
            # 異常な通信パターンを検出
            self._detect_anomalous_patterns(recent_conversations)
            
        except Exception as e:
            self.logger.warning(f"Error monitoring conversations: {e}")

    def _check_sender_cli_violations(self) -> None:
        """sender CLI違反をチェック"""
        try:
            violations = self.conversation_manager.conversation_logger.enforce_sender_cli_usage()
            
            if violations:
                self.logger.warning(
                    f"Found {len(violations)} sender CLI violations",
                    violation_count=len(violations)
                )
                
                # 違反処理（警告など）
                for violation in violations[-5:]:  # 最新5件のみ処理
                    self._handle_violation(violation)
                    
        except Exception as e:
            self.logger.warning(f"Error checking sender CLI violations: {e}")

    def _periodic_stats_report(self) -> None:
        """定期統計レポート"""
        try:
            # 5分ごとに統計を出力
            current_time = time.time()
            if not hasattr(self, '_last_stats_time'):
                self._last_stats_time = current_time
                return
                
            if current_time - self._last_stats_time >= 300:  # 5分
                stats = self.conversation_manager.get_conversation_summary()
                self.logger.info(f"Conversation stats report: {stats}")
                self._last_stats_time = current_time
                
        except Exception as e:
            self.logger.warning(f"Error generating stats report: {e}")

    def _detect_anomalous_patterns(self, conversations: list[Dict[str, Any]]) -> None:
        """異常な通信パターンを検出
        
        Args:
            conversations: 会話リスト
        """
        try:
            # パターン1: 同じbee間での短時間大量通信
            bee_pair_counts = {}
            for conv in conversations:
                pair = f"{conv['from_bee']}->{conv['to_bee']}"
                bee_pair_counts[pair] = bee_pair_counts.get(pair, 0) + 1
            
            for pair, count in bee_pair_counts.items():
                if count > 5:  # 短時間で5回以上
                    self.logger.warning(
                        f"High frequency communication detected: {pair}",
                        count=count,
                        pattern_type="high_frequency"
                    )
            
            # パターン2: sender CLI非使用率の高いbee
            cli_violations_by_bee = {}
            for conv in conversations:
                if not conv.get("sender_cli_used", True):
                    from_bee = conv["from_bee"]
                    cli_violations_by_bee[from_bee] = cli_violations_by_bee.get(from_bee, 0) + 1
            
            for bee, violation_count in cli_violations_by_bee.items():
                if violation_count > 2:
                    self.logger.warning(
                        f"Repeated CLI violations by {bee}",
                        bee=bee,
                        violation_count=violation_count,
                        pattern_type="repeated_cli_violation"
                    )
                    
        except Exception as e:
            self.logger.warning(f"Error detecting anomalous patterns: {e}")

    def _handle_violation(self, violation: Dict[str, Any]) -> None:
        """違反を処理
        
        Args:
            violation: 違反情報
        """
        from_bee = violation["from_bee"]
        to_bee = violation["to_bee"]
        message_id = violation["message_id"]
        
        self.logger.warning(
            f"Processing violation: {from_bee} -> {to_bee}",
            message_id=message_id
        )
        
        # TODO: 具体的な違反処理（警告送信、レポート生成など）

    def _cleanup(self) -> None:
        """クリーンアップ処理"""
        try:
            self.conversation_manager.shutdown()
            self.logger.info("Conversation daemon cleanup completed")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    def get_status(self) -> Dict[str, Any]:
        """デーモンの状態を取得
        
        Returns:
            Dict[str, Any]: 状態情報
        """
        try:
            stats = self.conversation_manager.conversation_logger.get_conversation_stats()
            return {
                "running": self.running,
                "stats": stats,
                "daemon_uptime": getattr(self, '_start_time', time.time()),
                "timestamp": time.time()
            }
        except Exception as e:
            self.logger.error(f"Failed to get daemon status: {e}")
            return {"running": self.running, "error": str(e)}


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Beehive Conversation Daemon")
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--interval", 
        type=float, 
        default=2.0,
        help="Monitoring interval in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--intercept", 
        type=str,
        help="Intercept a single beekeeper command and exit"
    )
    parser.add_argument(
        "--target", 
        type=str, 
        default="all",
        help="Target bee for intercepted command (default: all)"
    )
    parser.add_argument(
        "--status", 
        action="store_true",
        help="Show daemon status and exit"
    )
    
    args = parser.parse_args()
    
    try:
        daemon = ConversationDaemon(args.config)
        
        if args.status:
            # ステータス表示
            status = daemon.get_status()
            print(f"Daemon Status: {status}")
            return
            
        if args.intercept:
            # 単発コマンド傍受
            success = daemon.intercept_beekeeper_command(args.intercept, args.target)
            print(f"Command intercepted: {'SUCCESS' if success else 'FAILED'}")
            return
        
        # デーモンモード
        daemon._start_time = time.time()
        daemon.start(args.interval)
        
    except KeyboardInterrupt:
        print("\nDaemon stopped by user")
    except Exception as e:
        print(f"Daemon failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()