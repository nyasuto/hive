# 🛡️ Beehive 運用ガイド

Claude Multi-Agent Development System の本番運用・監視・トラブルシューティングガイド

## 📋 目次

- [システム監視](#システム監視)
- [ヘルスチェック](#ヘルスチェック)
- [パフォーマンス管理](#パフォーマンス管理)
- [トラブルシューティング](#トラブルシューティング)
- [運用自動化](#運用自動化)
- [セキュリティ対策](#セキュリティ対策)

---

## システム監視

### 1. 基本監視項目

#### Beehive システム状態

```bash
# システム全体状態確認
./beehive.sh status

# 詳細状態（JSON形式）
python -c "
from bees.queen_bee import QueenBee
queen = QueenBee('queen')
import json
status = queen.get_system_status()
print(json.dumps(status, indent=2, ensure_ascii=False))
"
```

#### tmux セッション監視

```bash
# セッション存在確認
tmux has-session -t beehive 2>/dev/null && echo "✅ Active" || echo "❌ Inactive"

# ペイン状態確認
tmux list-panes -t beehive -F "#{pane_id}: #{pane_title} (#{pane_width}x#{pane_height})"

# 各ペインの生存確認
for pane in 0.0 0.1 0.2 0.3; do
    tmux send-keys -t beehive:$pane "echo 'heartbeat-$(date)'" C-m
done
```

### 2. データベース監視

#### 接続・整合性チェック

```bash
# データベースファイル確認
ls -la hive/hive_memory.db

# 基本整合性チェック
sqlite3 hive/hive_memory.db "PRAGMA integrity_check;"

# テーブル存在確認
sqlite3 hive/hive_memory.db ".tables"
```

#### データ監視クエリ

```sql
-- アクティブタスク数
SELECT status, COUNT(*) as count 
FROM tasks 
GROUP BY status;

-- Bee状態確認
SELECT bee_name, status, last_heartbeat, 
       (julianday('now') - julianday(last_heartbeat)) * 1440 as minutes_since_heartbeat
FROM bee_states;

-- 未処理メッセージ数
SELECT to_bee, COUNT(*) as unprocessed_count
FROM bee_messages 
WHERE processed = FALSE 
GROUP BY to_bee;

-- send-keys通信ログ（最新10件）
SELECT timestamp, session_name, pane_id, 
       substr(message_content, 1, 50) as message_preview
FROM send_keys_log 
ORDER BY timestamp DESC 
LIMIT 10;
```

### 3. ログ監視

#### リアルタイムログ監視

```bash
# メインログ監視
tail -f logs/beehive.log | jq -r '.timestamp + " [" + .level + "] " + .message'

# エラーログフィルタ
tail -f logs/beehive.log | grep -E "(ERROR|CRITICAL)" | jq .

# 特定Beeのログフィルタ
tail -f logs/beehive.log | jq 'select(.bee_name == "queen")'
```

#### ログ解析スクリプト

```python
#!/usr/bin/env python3
# scripts/log_analyzer.py
import json
import sys
from datetime import datetime, timedelta
from collections import Counter

def analyze_logs(log_file_path, hours=24):
    """ログ解析スクリプト"""
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    error_counts = Counter()
    bee_activity = Counter()
    event_types = Counter()
    
    with open(log_file_path) as f:
        for line in f:
            try:
                log = json.loads(line)
                log_time = datetime.fromisoformat(log['timestamp'])
                
                if log_time < cutoff_time:
                    continue
                
                # エラー集計
                if log['level'] in ['ERROR', 'CRITICAL']:
                    error_counts[log.get('message', 'Unknown')] += 1
                
                # Bee活動集計
                bee_activity[log.get('bee_name', 'unknown')] += 1
                
                # イベントタイプ集計
                if 'event_type' in log:
                    event_types[log['event_type']] += 1
                    
            except (json.JSONDecodeError, KeyError):
                continue
    
    print(f"📊 Log Analysis (Last {hours} hours)")
    print(f"🔴 Errors: {sum(error_counts.values())}")
    print(f"📈 Bee Activity: {dict(bee_activity)}")
    print(f"🎯 Top Events: {dict(event_types.most_common(5))}")
    
    if error_counts:
        print(f"⚠️  Top Errors:")
        for error, count in error_counts.most_common(5):
            print(f"  {count}x: {error[:80]}")

if __name__ == "__main__":
    log_path = sys.argv[1] if len(sys.argv) > 1 else "logs/beehive.log"
    analyze_logs(log_path)
```

---

## ヘルスチェック

### 1. 自動ヘルスチェック

#### ヘルスチェックスクリプト

```bash
#!/bin/bash
# scripts/health_check.sh

echo "🏥 Beehive Health Check - $(date)"
echo "================================"

# 1. tmux セッション確認
if tmux has-session -t beehive 2>/dev/null; then
    echo "✅ tmux session: Active"
else
    echo "❌ tmux session: Inactive"
    exit 1
fi

# 2. データベース接続確認
if python -c "import sqlite3; sqlite3.connect('hive/hive_memory.db').execute('SELECT 1').fetchone()" 2>/dev/null; then
    echo "✅ Database: Accessible"
else
    echo "❌ Database: Connection failed"
    exit 1
fi

# 3. Bee状態確認
dead_bees=$(sqlite3 hive/hive_memory.db "
SELECT COUNT(*) FROM bee_states 
WHERE (julianday('now') - julianday(last_heartbeat)) * 1440 > 10
")

if [ "$dead_bees" -eq 0 ]; then
    echo "✅ Bee heartbeats: All active"
else
    echo "⚠️  Bee heartbeats: $dead_bees bees silent >10min"
fi

# 4. ログエラー確認
recent_errors=$(tail -n 100 logs/beehive.log | grep -c "ERROR\|CRITICAL" || echo 0)
if [ "$recent_errors" -lt 5 ]; then
    echo "✅ Recent errors: $recent_errors (acceptable)"
else
    echo "⚠️  Recent errors: $recent_errors (investigate)"
fi

# 5. 未処理メッセージ確認
unprocessed_messages=$(sqlite3 hive/hive_memory.db "
SELECT COUNT(*) FROM bee_messages WHERE processed = FALSE
")

if [ "$unprocessed_messages" -lt 10 ]; then
    echo "✅ Unprocessed messages: $unprocessed_messages"
else
    echo "⚠️  Unprocessed messages: $unprocessed_messages (backlog)"
fi

echo "================================"
echo "🎯 Health check completed"
```

### 2. システムメトリクス

#### リソース使用量監視

```python
#!/usr/bin/env python3
# scripts/system_metrics.py
import psutil
import sqlite3
import json
from datetime import datetime

def collect_system_metrics():
    """システムメトリクス収集"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "processes": [],
        "database": {}
    }
    
    # Claudeプロセス監視
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        if 'claude' in proc.info['name'].lower():
            metrics["processes"].append(proc.info)
    
    # データベースサイズ
    try:
        import os
        db_size = os.path.getsize("hive/hive_memory.db")
        metrics["database"]["size_mb"] = db_size / (1024 * 1024)
        
        # レコード数
        conn = sqlite3.connect("hive/hive_memory.db")
        for table in ["tasks", "bee_messages", "bee_states", "send_keys_log"]:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            metrics["database"][f"{table}_count"] = cursor.fetchone()[0]
        conn.close()
        
    except Exception as e:
        metrics["database"]["error"] = str(e)
    
    return metrics

if __name__ == "__main__":
    metrics = collect_system_metrics()
    print(json.dumps(metrics, indent=2))
```

---

## パフォーマンス管理

### 1. パフォーマンス監視

#### 応答時間測定

```python
#!/usr/bin/env python3
# scripts/performance_test.py
import time
import statistics
from bees.queen_bee import QueenBee

def measure_response_times():
    """各操作の応答時間測定"""
    queen = QueenBee("queen")
    
    # タスク作成応答時間
    task_creation_times = []
    for i in range(10):
        start = time.time()
        task_id = queen.create_task(
            f"Performance test task {i}",
            "Test task for performance measurement",
            "low"
        )
        end = time.time()
        task_creation_times.append(end - start)
    
    # メッセージ送信応答時間
    message_times = []
    for i in range(10):
        start = time.time()
        queen.send_message(
            "developer",
            "test",
            f"Performance test {i}",
            "Test message content"
        )
        end = time.time()
        message_times.append(end - start)
    
    print("📊 Performance Metrics")
    print(f"Task Creation - Avg: {statistics.mean(task_creation_times):.3f}s, Max: {max(task_creation_times):.3f}s")
    print(f"Message Send - Avg: {statistics.mean(message_times):.3f}s, Max: {max(message_times):.3f}s")

if __name__ == "__main__":
    measure_response_times()
```

### 2. 負荷対策

#### 同時実行制御

```python
# bees/performance_manager.py
import asyncio
import threading
from typing import Dict, Any
from datetime import datetime, timedelta

class PerformanceManager:
    """パフォーマンス管理クラス"""
    
    def __init__(self):
        self.operation_counts = {}
        self.rate_limits = {
            "task_creation": {"max": 10, "window": 60},  # 1分間に10タスクまで
            "message_send": {"max": 50, "window": 60},   # 1分間に50メッセージまで
        }
        self.lock = threading.Lock()
    
    def check_rate_limit(self, operation: str) -> bool:
        """レート制限チェック"""
        with self.lock:
            now = datetime.now()
            
            if operation not in self.operation_counts:
                self.operation_counts[operation] = []
            
            # 古い記録を削除
            cutoff = now - timedelta(seconds=self.rate_limits[operation]["window"])
            self.operation_counts[operation] = [
                ts for ts in self.operation_counts[operation] if ts > cutoff
            ]
            
            # 制限チェック
            if len(self.operation_counts[operation]) >= self.rate_limits[operation]["max"]:
                return False
            
            # 記録追加
            self.operation_counts[operation].append(now)
            return True

# 使用例
performance_manager = PerformanceManager()

def rate_limited_task_creation(queen, title, description):
    """レート制限付きタスク作成"""
    if not performance_manager.check_rate_limit("task_creation"):
        raise Exception("Rate limit exceeded for task creation")
    
    return queen.create_task(title, description)
```

---

## トラブルシューティング

### 1. 一般的な問題と対処法

#### tmux セッション問題

```bash
# 問題: セッションが応答しない
# 診断
tmux list-sessions
tmux list-panes -t beehive
tmux capture-pane -t beehive:0.0 -p

# 対処: 段階的復旧
# 1. 強制終了・再作成
tmux kill-session -t beehive
./beehive.sh init

# 2. 個別ペイン再起動
tmux send-keys -t beehive:0.0 C-c
tmux send-keys -t beehive:0.0 "claude --dangerously-skip-permissions" C-m
```

#### データベース問題

```bash
# 問題: データベース破損
# 診断
sqlite3 hive/hive_memory.db "PRAGMA integrity_check;"

# 対処: バックアップ復元
cp hive/hive_memory.db hive/hive_memory.db.corrupt
cp backups/hive_memory_$(date +%Y%m%d).db hive/hive_memory.db

# 緊急時: 新規データベース作成
rm hive/hive_memory.db
python bees/init_test_db.py
```

#### Bee応答停止

```bash
# 問題: 特定Beeが応答しない
# 診断
sqlite3 hive/hive_memory.db "
SELECT bee_name, last_heartbeat,
       (julianday('now') - julianday(last_heartbeat)) * 1440 as minutes_ago
FROM bee_states 
WHERE bee_name = 'developer';
"

# 対処: Bee再起動
# 1. 対象ペインにフォーカス
tmux select-pane -t beehive:0.1

# 2. プロセス終了・再起動
tmux send-keys -t beehive:0.1 C-c
tmux send-keys -t beehive:0.1 "claude --dangerously-skip-permissions" C-m

# 3. 役割再注入
python -m bees.cli send beehive 0.1 "$(cat roles/developer.md)" --type role_injection
```

### 2. エラー分析

#### エラーパターン分析

```python
#!/usr/bin/env python3
# scripts/error_analyzer.py
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

def analyze_error_patterns(log_file):
    """エラーパターン解析"""
    errors_by_hour = defaultdict(list)
    error_types = Counter()
    bee_errors = defaultdict(Counter)
    
    with open(log_file) as f:
        for line in f:
            try:
                log = json.loads(line)
                if log['level'] in ['ERROR', 'CRITICAL']:
                    # 時間別集計
                    hour = datetime.fromisoformat(log['timestamp']).hour
                    errors_by_hour[hour].append(log)
                    
                    # エラータイプ分類
                    message = log['message']
                    if 'database' in message.lower():
                        error_types['database'] += 1
                    elif 'tmux' in message.lower():
                        error_types['tmux'] += 1
                    elif 'timeout' in message.lower():
                        error_types['timeout'] += 1
                    else:
                        error_types['other'] += 1
                    
                    # Bee別エラー
                    bee_name = log.get('bee_name', 'unknown')
                    bee_errors[bee_name][message[:50]] += 1
                    
            except (json.JSONDecodeError, KeyError):
                continue
    
    # レポート出力
    print("🔍 Error Pattern Analysis")
    print("=" * 50)
    
    print("📊 Errors by Hour:")
    for hour in sorted(errors_by_hour.keys()):
        print(f"  {hour:02d}:00 - {len(errors_by_hour[hour])} errors")
    
    print("\n📂 Error Types:")
    for error_type, count in error_types.most_common():
        print(f"  {error_type}: {count}")
    
    print("\n🐝 Errors by Bee:")
    for bee_name, errors in bee_errors.items():
        print(f"  {bee_name}: {sum(errors.values())} total")
        for error, count in errors.most_common(3):
            print(f"    {count}x: {error}")

if __name__ == "__main__":
    analyze_error_patterns("logs/beehive.log")
```

---

## 運用自動化

### 1. 定期メンテナンス

#### 自動バックアップ

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# データベースバックアップ
cp hive/hive_memory.db $BACKUP_DIR/hive_memory_$DATE.db

# ログローテーション
if [ -f logs/beehive.log ]; then
    cp logs/beehive.log $BACKUP_DIR/beehive_$DATE.log
    > logs/beehive.log  # ログファイルをクリア
fi

# 古いバックアップ削除（30日以上）
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.log" -mtime +30 -delete

echo "✅ Backup completed: $DATE"
```

#### 定期ヘルスチェック（cron）

```bash
# crontab エントリ例

# 5分ごとのヘルスチェック
*/5 * * * * /path/to/hive/scripts/health_check.sh >> /var/log/beehive_health.log 2>&1

# 毎時のシステムメトリクス収集
0 * * * * /path/to/hive/scripts/system_metrics.py >> /var/log/beehive_metrics.log 2>&1

# 日次バックアップ
0 2 * * * /path/to/hive/scripts/backup.sh >> /var/log/beehive_backup.log 2>&1

# 週次ログ解析
0 3 * * 0 /path/to/hive/scripts/log_analyzer.py logs/beehive.log > /var/log/beehive_weekly_analysis.log
```

### 2. アラート設定

#### アラート通知スクリプト

```python
#!/usr/bin/env python3
# scripts/alert_manager.py
import smtplib
import json
from email.mime.text import MIMEText
from datetime import datetime
import subprocess

class AlertManager:
    """アラート管理クラス"""
    
    def __init__(self, config_file="alert_config.json"):
        with open(config_file) as f:
            self.config = json.load(f)
    
    def check_critical_conditions(self):
        """重要な状態をチェック"""
        alerts = []
        
        # tmuxセッション確認
        try:
            subprocess.run(["tmux", "has-session", "-t", "beehive"], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            alerts.append({
                "level": "CRITICAL",
                "message": "Beehive tmux session is down",
                "timestamp": datetime.now().isoformat()
            })
        
        # データベース接続確認
        try:
            import sqlite3
            conn = sqlite3.connect("hive/hive_memory.db", timeout=5)
            conn.execute("SELECT 1").fetchone()
            conn.close()
        except Exception as e:
            alerts.append({
                "level": "CRITICAL", 
                "message": f"Database connection failed: {e}",
                "timestamp": datetime.now().isoformat()
            })
        
        return alerts
    
    def send_alert(self, alert):
        """アラート送信"""
        if self.config.get("email_enabled"):
            self._send_email_alert(alert)
        
        if self.config.get("webhook_enabled"):
            self._send_webhook_alert(alert)
    
    def _send_email_alert(self, alert):
        """メールアラート送信"""
        msg = MIMEText(f"""
Beehive System Alert
        
Level: {alert['level']}
Message: {alert['message']}
Time: {alert['timestamp']}
        """)
        
        msg['Subject'] = f"[Beehive Alert] {alert['level']}: {alert['message'][:50]}"
        msg['From'] = self.config['email']['from']
        msg['To'] = self.config['email']['to']
        
        server = smtplib.SMTP(self.config['email']['smtp_server'])
        server.send_message(msg)
        server.quit()

if __name__ == "__main__":
    alert_manager = AlertManager()
    alerts = alert_manager.check_critical_conditions()
    
    for alert in alerts:
        alert_manager.send_alert(alert)
        print(f"🚨 Alert sent: {alert['level']} - {alert['message']}")
```

---

## セキュリティ対策

### 1. セキュリティチェック

#### セキュリティ監査スクリプト

```bash
#!/bin/bash
# scripts/security_audit.sh

echo "🔒 Beehive Security Audit - $(date)"
echo "================================"

# 1. ファイル権限確認
echo "📋 File Permissions:"
ls -la hive/hive_memory.db
ls -la logs/
ls -la scripts/

# 2. プロセス確認
echo -e "\n🔍 Running Processes:"
ps aux | grep -E "(claude|tmux|beehive)" | grep -v grep

# 3. ネットワーク接続確認
echo -e "\n🌐 Network Connections:"
netstat -tulpn | grep -E ":80|:443|:22" || echo "No suspicious connections"

# 4. ログ内の機密情報確認
echo -e "\n🕵️ Checking for secrets in logs:"
if grep -iE "(password|token|key|secret)" logs/beehive.log; then
    echo "⚠️ Potential secrets found in logs"
else
    echo "✅ No obvious secrets in logs"
fi

# 5. データベース内の機密情報確認
echo -e "\n🗄️ Checking database for sensitive data:"
sqlite3 hive/hive_memory.db "
SELECT 'Tasks' as table_name, COUNT(*) as count FROM tasks WHERE description LIKE '%password%' OR description LIKE '%secret%'
UNION ALL
SELECT 'Messages' as table_name, COUNT(*) as count FROM bee_messages WHERE content LIKE '%password%' OR content LIKE '%secret%'
"

echo "================================"
echo "🔒 Security audit completed"
```

### 2. アクセス制御

#### 権限管理

```bash
# ファイル権限設定
chmod 700 hive/                    # データベースディレクトリ
chmod 600 hive/hive_memory.db      # データベースファイル
chmod 640 logs/beehive.log          # ログファイル
chmod 750 scripts/*.sh             # 実行スクリプト

# 所有者設定
chown -R beehive:beehive hive/
chown -R beehive:beehive logs/
```

### 3. データ保護

#### 機密データ削除

```python
#!/usr/bin/env python3
# scripts/data_sanitizer.py
import sqlite3
import re

def sanitize_database():
    """データベースから機密情報を削除"""
    conn = sqlite3.connect("hive/hive_memory.db")
    
    # 機密情報パターン
    sensitive_patterns = [
        r'password\s*[:=]\s*\S+',
        r'token\s*[:=]\s*\S+',
        r'api[_-]?key\s*[:=]\s*\S+',
        r'secret\s*[:=]\s*\S+'
    ]
    
    # タスクテーブルのサニタイズ
    cursor = conn.execute("SELECT task_id, description FROM tasks")
    for task_id, description in cursor.fetchall():
        if description:
            sanitized = description
            for pattern in sensitive_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
            
            if sanitized != description:
                conn.execute(
                    "UPDATE tasks SET description = ? WHERE task_id = ?",
                    (sanitized, task_id)
                )
    
    # メッセージテーブルのサニタイズ
    cursor = conn.execute("SELECT message_id, content FROM bee_messages")
    for message_id, content in cursor.fetchall():
        if content:
            sanitized = content
            for pattern in sensitive_patterns:
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
            
            if sanitized != content:
                conn.execute(
                    "UPDATE bee_messages SET content = ? WHERE message_id = ?",
                    (sanitized, message_id)
                )
    
    conn.commit()
    conn.close()
    print("✅ Database sanitization completed")

if __name__ == "__main__":
    sanitize_database()
```

---

## 📚 運用チェックリスト

### 日次チェック
- [ ] システム状態確認 (`./beehive.sh status`)
- [ ] エラーログ確認 (`grep ERROR logs/beehive.log`)
- [ ] ディスク使用量確認
- [ ] Bee応答確認

### 週次チェック
- [ ] パフォーマンスメトリクス確認
- [ ] データベース整合性チェック
- [ ] セキュリティログ確認
- [ ] バックアップ動作確認

### 月次チェック
- [ ] ログローテーション実行
- [ ] 古いバックアップ削除
- [ ] システムリソース確認
- [ ] セキュリティ監査実行

---

## 🚨 緊急対応手順

### 1. システム完全停止時

```bash
# 1. 現状確認
./beehive.sh status
tmux list-sessions

# 2. 強制停止・クリーンアップ
tmux kill-session -t beehive
pkill -f claude

# 3. データベースバックアップ
cp hive/hive_memory.db backups/emergency_backup_$(date +%Y%m%d_%H%M%S).db

# 4. システム再起動
./beehive.sh init

# 5. 動作確認
./beehive.sh status
```

### 2. データベース破損時

```bash
# 1. 破損ファイル退避
mv hive/hive_memory.db hive/hive_memory.db.corrupt

# 2. 最新バックアップ復元
cp backups/hive_memory_$(ls backups/ | grep hive_memory | tail -1) hive/hive_memory.db

# 3. 整合性確認
sqlite3 hive/hive_memory.db "PRAGMA integrity_check;"

# 4. システム再起動
./beehive.sh stop
./beehive.sh init
```

---

## 📞 サポート・エスカレーション

### 1. ログ収集

```bash
# 緊急時ログパッケージ作成
tar -czf beehive_emergency_$(date +%Y%m%d_%H%M%S).tar.gz \
    logs/ \
    hive/hive_memory.db \
    scripts/health_check.sh \
    --exclude="*.tmp"
```

### 2. 問題報告テンプレート

```markdown
## Beehive 問題報告

**発生時刻**: YYYY-MM-DD HH:MM:SS
**症状**: [問題の詳細説明]
**影響範囲**: [影響を受けるBee・機能]
**再現手順**: 
1. [手順1]
2. [手順2]

**ログ情報**:
```bash
# 最新エラーログ
tail -n 50 logs/beehive.log | grep ERROR

# システム状態
./beehive.sh status
```

**実行した対処**:
- [対処内容1]
- [対処内容2]

**添付ファイル**: beehive_emergency_YYYYMMDD_HHMMSS.tar.gz
```

---

## 📚 関連ドキュメント

### 🛠️ 技術理解
- **[開発者ガイドアーキテクチャ](developer_guide.md#アーキテクチャ理解)** - システム構造の詳細理解
- **[API Reference](api_reference.md)** - 監視・診断API仕様

### 🎓 学習・研修
- **[チュートリアル](tutorial.md)** - 基本操作の体験学習（3-4時間）
- **[開発者ガイドデバッグ](developer_guide.md#デバッグトラブルシューティング)** - 開発視点のトラブル対応

### 🔗 ナビゲーション
- **[ドキュメント目次](README.md)** - 全ドキュメント概要・対象読者別ガイド

### 📞 緊急時参照
- **[API Reference 例外クラス](api_reference.md#例外クラス)** - エラー種別・対処法
- **[開発者ガイド一般的問題](developer_guide.md#一般的な問題と対処法)** - 開発環境での類似問題

---

**🔄 最終更新**: 2025-07-23  
**📋 対象バージョン**: v1.0.0  
**🎯 想定読者**: システム管理者・運用担当者