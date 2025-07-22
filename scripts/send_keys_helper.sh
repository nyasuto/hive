#!/bin/bash
# send_keys_helper.sh - Shell script helper for send-keys CLI
# CLI経由でsend-keysを実行するためのヘルパー関数

# 設定
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_CLI="cd $PROJECT_ROOT && python -m bees.cli"

# エラーハンドリング
set -euo pipefail

# ヘルパー関数: CLI経由でsend-keys実行
send_keys_cli() {
    local session_name="$1"
    local target_pane="$2"
    local message="$3"
    local message_type="${4:-general}"
    local sender="${5:-system}"
    local dry_run="${6:-false}"
    
    # パラメータ検証
    if [[ -z "$session_name" || -z "$target_pane" || -z "$message" ]]; then
        echo "❌ Error: Missing required parameters"
        echo "Usage: send_keys_cli <session_name> <target_pane> <message> [message_type] [sender] [dry_run]"
        return 1
    fi
    
    
    # CLI実行 - 一時ファイルを使用して長いメッセージを安全に処理
    local temp_file=$(mktemp)
    echo "$message" > "$temp_file"
    
    # CLIに一時ファイルから読み込ませる
    cd "$PROJECT_ROOT"
    if [[ "$dry_run" == "true" ]]; then
        python -m bees.cli send "$session_name" "$target_pane" "$(cat "$temp_file")" --type "$message_type" --sender "$sender" --dry-run
    else
        python -m bees.cli send "$session_name" "$target_pane" "$(cat "$temp_file")" --type "$message_type" --sender "$sender"
    fi
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Message sent to $session_name:$target_pane"
        rm -f "$temp_file"
        return 0
    else
        echo "❌ Failed to send message"
        rm -f "$temp_file"
        return 1
    fi
}

# 役割注入用のヘルパー
inject_role() {
    local session_name="$1"
    local target_pane="$2"
    local role_message="$3"
    local dry_run="${4:-false}"
    
    send_keys_cli "$session_name" "$target_pane" "$role_message" "role_injection" "system" "$dry_run"
}

# タスク割り当て用のヘルパー
assign_task() {
    local session_name="$1"
    local target_pane="$2"
    local task_message="$3"
    local sender="${4:-queen}"
    local dry_run="${5:-false}"
    
    send_keys_cli "$session_name" "$target_pane" "$task_message" "task_assignment" "$sender" "$dry_run"
}

# 通知送信用のヘルパー
send_notification() {
    local session_name="$1"
    local target_pane="$2"
    local notification="$3"
    local sender="${4:-system}"
    local dry_run="${5:-false}"
    
    send_keys_cli "$session_name" "$target_pane" "$notification" "notification" "$sender" "$dry_run"
}

# ログ表示用のヘルパー
show_send_keys_logs() {
    local session_name="${1:-}"
    local limit="${2:-20}"
    
    if [[ -n "$session_name" ]]; then
        eval "cd $PROJECT_ROOT && python -m bees.cli logs --session '$session_name' --limit '$limit'"
    else
        eval "cd $PROJECT_ROOT && python -m bees.cli logs --limit '$limit'"
    fi
}

# 使用例の表示
show_usage() {
    cat << EOF
🐝 Beehive Send-Keys Helper Functions

Available functions:
  send_keys_cli <session> <pane> <message> [type] [sender] [dry_run]
      - General send-keys with CLI
  
  inject_role <session> <pane> <role_message> [dry_run]
      - Inject role to agent
  
  assign_task <session> <pane> <task_message> [sender] [dry_run]
      - Assign task to agent
  
  send_notification <session> <pane> <notification> [sender] [dry_run]
      - Send notification to agent
  
  show_send_keys_logs [session] [limit]
      - Show recent send-keys logs

Examples:
  # 役割注入
  inject_role "beehive" "0.0" "You are Queen Bee. Plan and coordinate tasks."
  
  # タスク割り当て
  assign_task "beehive" "0.1" "Implement user authentication feature"
  
  # 通知送信
  send_notification "beehive" "0.2" "Tests completed successfully"
  
  # ログ表示
  show_send_keys_logs "beehive" 10

Set BEEHIVE_DRY_RUN=true for dry run mode.
EOF
}

# メイン関数
main() {
    case "${1:-help}" in
        "send")
            shift
            send_keys_cli "$@"
            ;;
        "role")
            shift
            inject_role "$@"
            ;;
        "task")
            shift
            assign_task "$@"
            ;;
        "notify")
            shift
            send_notification "$@"
            ;;
        "logs")
            shift
            show_send_keys_logs "$@"
            ;;
        "help"|*)
            show_usage
            ;;
    esac
}

# スクリプトとして実行された場合
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi