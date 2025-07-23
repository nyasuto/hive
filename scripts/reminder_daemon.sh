#!/bin/bash
# reminder_daemon.sh - Beehive定期リマインダーデーモン
# Issue #5: 定期的なコンテキストリマインダーシステム

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_NAME="beehive"
REMINDER_INTERVAL=300  # 5分（秒）

# ログとPIDファイルの設定
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/reminder_daemon.log"
PID_FILE="$LOG_DIR/reminder_daemon.pid"

# ログディレクトリ作成
mkdir -p "$LOG_DIR"

# ログ関数
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" | tee -a "$LOG_FILE"
}

# PIDファイル管理
save_pid() {
    echo $$ > "$PID_FILE"
    log_info "デーモン開始 (PID: $$)"
}

cleanup() {
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        log_info "デーモン終了 (PID: $$)"
    fi
}

# シグナルハンドラー
trap cleanup EXIT
trap 'log_info "デーモン停止要求を受信"; exit 0' TERM INT

# デーモンの状態チェック
check_daemon_status() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "デーモンは実行中です (PID: $pid)"
            return 0
        else
            echo "PIDファイルが存在しますが、プロセスが見つかりません"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo "デーモンは実行されていません"
        return 1
    fi
}

# デーモンの停止
stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "デーモンを停止しています (PID: $pid)"
            kill "$pid"
            
            # 停止を待機
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "デーモンが応答しません。強制終了します"
                kill -9 "$pid"
            fi
            
            rm -f "$PID_FILE"
            log_info "デーモンを停止しました"
        else
            log_warning "PIDファイルが存在しますが、プロセスが見つかりません"
            rm -f "$PID_FILE"
        fi
    else
        echo "デーモンは実行されていません"
    fi
}

# tmuxセッションの存在確認
check_tmux_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 単発リマインダー送信
send_immediate_reminder() {
    log_info "即座にリマインダーを送信します"
    
    cd "$PROJECT_ROOT"
    if python -m memory.context_manager --remind-all; then
        log_info "リマインダー送信完了"
        return 0
    else
        log_error "リマインダー送信に失敗しました"
        return 1
    fi
}

# 定期リマインダーデーモンの開始
start_daemon() {
    local interval="${1:-$REMINDER_INTERVAL}"
    
    # 既存のデーモンをチェック
    if check_daemon_status >/dev/null 2>&1; then
        echo "デーモンは既に実行中です"
        exit 1
    fi
    
    log_info "リマインダーデーモンを開始します"
    log_info "間隔: ${interval}秒 ($(($interval / 60))分)"
    log_info "ログファイル: $LOG_FILE"
    log_info "PIDファイル: $PID_FILE"
    
    save_pid
    
    cd "$PROJECT_ROOT"
    
    # 定期実行ループ
    while true; do
        if check_tmux_session; then
            log_info "定期リマインダーを実行中..."
            
            if python -m memory.context_manager --remind-all; then
                log_info "定期リマインダー送信完了"
            else
                log_error "定期リマインダー送信に失敗しました"
            fi
        else
            log_warning "tmuxセッション '$SESSION_NAME' が見つかりません。リマインダーをスキップします"
        fi
        
        log_info "次のリマインダーまで ${interval}秒 ($(($interval / 60))分) 待機します"
        sleep "$interval"
    done
}

# ヘルプ表示
show_help() {
    cat << 'EOF'
🐝 Beehive Reminder Daemon

USAGE:
    ./scripts/reminder_daemon.sh <command> [options]

COMMANDS:
    start [interval]    デーモンを開始 (デフォルト: 300秒/5分)
    stop               デーモンを停止
    status             デーモンの状態を確認
    restart [interval] デーモンを再起動
    remind             即座にリマインダーを送信
    logs [lines]       ログを表示 (デフォルト: 20行)

EXAMPLES:
    ./scripts/reminder_daemon.sh start           # 5分間隔でデーモン開始
    ./scripts/reminder_daemon.sh start 180      # 3分間隔でデーモン開始
    ./scripts/reminder_daemon.sh stop           # デーモン停止
    ./scripts/reminder_daemon.sh status         # 状態確認
    ./scripts/reminder_daemon.sh remind         # 即座にリマインダー送信
    ./scripts/reminder_daemon.sh logs 50        # 最新50行のログ表示

FILES:
    Log: $LOG_FILE
    PID: $PID_FILE

NOTE:
    デーモンはtmuxセッション 'beehive' が存在する時のみリマインダーを送信します。
    セッションが見つからない場合は警告を出力し、次の周期まで待機します。
EOF
}

# ログ表示
show_logs() {
    local lines="${1:-20}"
    
    if [ -f "$LOG_FILE" ]; then
        echo "=== Reminder Daemon Logs (最新 $lines 行) ==="
        tail -n "$lines" "$LOG_FILE"
    else
        echo "ログファイルが見つかりません: $LOG_FILE"
    fi
}

# メイン処理
main() {
    local command="${1:-help}"
    
    case "$command" in
        "start")
            local interval="${2:-$REMINDER_INTERVAL}"
            start_daemon "$interval"
            ;;
        "stop")
            stop_daemon
            ;;
        "status")
            check_daemon_status
            ;;
        "restart")
            local interval="${2:-$REMINDER_INTERVAL}"
            stop_daemon
            sleep 2
            start_daemon "$interval"
            ;;
        "remind")
            send_immediate_reminder
            ;;
        "logs")
            local lines="${2:-20}"
            show_logs "$lines"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo "不明なコマンド: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# エラーハンドリング
trap 'log_error "予期しないエラーが発生しました (line: $LINENO)"' ERR

# スクリプト実行
main "$@"