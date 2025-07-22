#!/bin/bash

# agent_poller.sh - Agent Task Polling System for Claude Multi-Agent System
# Allows agents to check for tasks and messages from the database
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 色付きログ関数
log_info() { echo -e "\033[36m[POLL]  \033[0m $1"; }
log_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }
log_warning() { echo -e "\033[33m[WARNING]\033[0m $1"; }

# エージェントのタスク確認
check_my_tasks() {
    local bee_name="${1:-}"
    
    if [[ -z "$bee_name" ]]; then
        log_error "Usage: check_my_tasks <bee_name>"
        return 1
    fi
    
    log_info "Checking tasks for $bee_name..."
    
    # 自分に割り当てられたアクティブなタスク
    local my_tasks
    my_tasks=$("$SCRIPT_DIR/task_manager.sh" list pending "$bee_name" 2>/dev/null || echo "")
    
    if [[ -n "$my_tasks" ]]; then
        echo "📋 あなたのアクティブなタスク:"
        echo "$my_tasks" | while IFS='|' read -r task_id title status priority _ created _; do
            if [[ -n "$task_id" && "$task_id" != "task_id" ]]; then
                echo "  [$task_id] $title (優先度: $priority)"
                echo "    作成日時: $created"
            fi
        done
    else
        echo "📋 現在割り当てられているタスクはありません"
    fi
    
    # 進行中のタスク
    local in_progress_tasks
    in_progress_tasks=$("$SCRIPT_DIR/task_manager.sh" list in_progress "$bee_name" 2>/dev/null || echo "")
    
    if [[ -n "$in_progress_tasks" ]]; then
        echo
        echo "🔄 進行中のタスク:"
        echo "$in_progress_tasks" | while IFS='|' read -r task_id title status priority _ created _; do
            if [[ -n "$task_id" && "$task_id" != "task_id" ]]; then
                echo "  [$task_id] $title (優先度: $priority)"
                echo "    作成日時: $created"
            fi
        done
    fi
}

# メッセージ確認
check_my_messages() {
    local bee_name="${1:-}"
    
    if [[ -z "$bee_name" ]]; then
        log_error "Usage: check_my_messages <bee_name>"
        return 1
    fi
    
    log_info "Checking messages for $bee_name..."
    
    local messages
    messages=$("$SCRIPT_DIR/task_manager.sh" messages "$bee_name" 2>/dev/null || echo "")
    
    if [[ -n "$messages" ]]; then
        echo "💬 未読メッセージ:"
        echo "$messages" | while IFS='|' read -r msg_id from_bee to_bee msg_type subject _ task_id priority created; do
            if [[ -n "$msg_id" && "$msg_id" != "message_id" ]]; then
                echo "  [ID: $msg_id] From: $from_bee"
                echo "    件名: $subject"
                echo "    種類: $msg_type (優先度: $priority)"
                if [[ -n "$task_id" && "$task_id" != "NULL" ]]; then
                    echo "    関連タスク: #$task_id"
                fi
                echo "    作成: $created"
                echo "    ---"
            fi
        done
    else
        echo "💬 新しいメッセージはありません"
    fi
}

# 状態更新
update_my_status() {
    local bee_name="${1:-}"
    local new_status="${2:-idle}"
    local task_id="${3:-}"
    
    if [[ -z "$bee_name" ]]; then
        log_error "Usage: update_my_status <bee_name> <status> [task_id]"
        return 1
    fi
    
    log_info "Updating $bee_name status to: $new_status"
    
    "$SCRIPT_DIR/task_manager.sh" bee-state "$bee_name" "$new_status" "$task_id"
    
    log_success "Status updated successfully"
}

# タスク開始
start_task() {
    local bee_name="${1:-}"
    local task_id="${2:-}"
    
    if [[ -z "$bee_name" || -z "$task_id" ]]; then
        log_error "Usage: start_task <bee_name> <task_id>"
        return 1
    fi
    
    log_info "$bee_name starting task $task_id..."
    
    # タスクステータスを進行中に更新
    "$SCRIPT_DIR/task_manager.sh" status "$task_id" "in_progress" "$bee_name" "作業を開始しました"
    
    # Beeステータス更新
    "$SCRIPT_DIR/task_manager.sh" bee-state "$bee_name" "busy" "$task_id" "50"
    
    log_success "Task $task_id started by $bee_name"
    
    # タスク詳細表示
    echo
    echo "📋 タスク詳細:"
    "$SCRIPT_DIR/task_manager.sh" details "$task_id"
}

# タスク完了
complete_task() {
    local bee_name="${1:-}"
    local task_id="${2:-}"
    local notes="${3:-作業完了}"
    
    if [[ -z "$bee_name" || -z "$task_id" ]]; then
        log_error "Usage: complete_task <bee_name> <task_id> [notes]"
        return 1
    fi
    
    log_info "$bee_name completing task $task_id..."
    
    # タスクステータスを完了に更新
    "$SCRIPT_DIR/task_manager.sh" status "$task_id" "completed" "$bee_name" "$notes"
    
    # Beeステータス更新
    "$SCRIPT_DIR/task_manager.sh" bee-state "$bee_name" "idle" "" "0"
    
    # Queen Beeに完了通知
    "$SCRIPT_DIR/task_manager.sh" message "$bee_name" "queen" "task_update" \
        "タスク完了報告" "タスク ID $task_id が完了しました。詳細: $notes" "$task_id"
    
    log_success "Task $task_id completed by $bee_name"
}

# メッセージ処理
process_message() {
    local message_id="${1:-}"
    
    if [[ -z "$message_id" ]]; then
        log_error "Usage: process_message <message_id>"
        return 1
    fi
    
    "$SCRIPT_DIR/task_manager.sh" processed "$message_id"
    log_success "Message $message_id marked as processed"
}

# 他のエージェントに通知
notify_agent() {
    local from_bee="${1:-}"
    local to_bee="${2:-}"
    local subject="${3:-}"
    local message="${4:-}"
    local task_id="${5:-}"
    
    if [[ -z "$from_bee" || -z "$to_bee" || -z "$subject" || -z "$message" ]]; then
        log_error "Usage: notify_agent <from> <to> <subject> <message> [task_id]"
        return 1
    fi
    
    log_info "Sending notification from $from_bee to $to_bee..."
    
    "$SCRIPT_DIR/task_manager.sh" message "$from_bee" "$to_bee" "info" "$subject" "$message" "$task_id"
    
    log_success "Notification sent successfully"
}

# 統合ダッシュボード
show_dashboard() {
    local bee_name="${1:-}"
    
    if [[ -z "$bee_name" ]]; then
        log_error "Usage: show_dashboard <bee_name>"
        return 1
    fi
    
    echo "🐝 $bee_name Dashboard"
    echo "==================="
    echo
    
    # 自分のタスク
    check_my_tasks "$bee_name"
    
    echo
    echo "==================="
    
    # メッセージ
    check_my_messages "$bee_name"
    
    echo
    echo "==================="
    
    # 現在の状態
    echo "📊 現在の状態:"
    local current_state
    current_state=$("$SCRIPT_DIR/task_manager.sh" bees | grep "^$bee_name|" || echo "")
    if [[ -n "$current_state" ]]; then
        echo "$current_state" | while IFS='|' read -r _ status task workload _ heartbeat; do
            echo "  ステータス: $status"
            echo "  ワークロード: ${workload}%"
            echo "  現在のタスク: ${task:-なし}"
            echo "  最終更新: $heartbeat"
        done
    fi
}

# 簡単なコマンド (agents向け)
quick_poll() {
    local bee_name="${1:-}"
    
    if [[ -z "$bee_name" ]]; then
        echo "🤖 Usage: ./scripts/agent_poller.sh poll <your_bee_name>"
        echo "例: ./scripts/agent_poller.sh poll queen"
        return 1
    fi
    
    echo "🔄 Polling for $bee_name..."
    echo
    
    # 新しいタスクをチェック
    local pending_count
    pending_count=$("$SCRIPT_DIR/task_manager.sh" list pending "$bee_name" 2>/dev/null | wc -l || echo "0")
    
    # メッセージをチェック
    local message_count
    message_count=$("$SCRIPT_DIR/task_manager.sh" messages "$bee_name" 2>/dev/null | wc -l || echo "0")
    
    echo "📋 ペンディングタスク: $pending_count 件"
    echo "💬 未読メッセージ: $message_count 件"
    
    if [[ "$pending_count" -gt 0 || "$message_count" -gt 0 ]]; then
        echo
        echo "詳細確認: ./scripts/agent_poller.sh dashboard $bee_name"
    fi
}

# ヘルプ表示
show_help() {
    cat << 'EOF'
🐝 Agent Poller - Task Polling System for Claude Multi-Agent System

USAGE:
    ./scripts/agent_poller.sh <command> [options]

COMMANDS:
    poll <bee_name>                Quick status check
    dashboard <bee_name>           Show full dashboard
    tasks <bee_name>              Show my tasks
    messages <bee_name>           Show my messages  
    start <bee_name> <task_id>    Start working on a task
    complete <bee_name> <task_id> [notes]
                                  Complete a task
    status <bee_name> <status> [task_id]
                                  Update my status
    notify <from> <to> <subject> <message> [task_id]
                                  Send notification
    process-msg <message_id>      Mark message as processed
    help                          Show this help

BEE NAMES: queen, developer, qa
STATUSES: idle, busy, waiting, offline, error

EXAMPLES FOR AGENTS:
    # Quick check for new work
    ./scripts/agent_poller.sh poll queen
    
    # See full dashboard
    ./scripts/agent_poller.sh dashboard developer
    
    # Start a task
    ./scripts/agent_poller.sh start developer 1
    
    # Update status
    ./scripts/agent_poller.sh status qa busy 2
    
    # Complete a task
    ./scripts/agent_poller.sh complete developer 1 "実装完了、テスト準備OK"
    
    # Send notification to Queen
    ./scripts/agent_poller.sh notify developer queen "作業完了" "タスク1の実装が完了しました" 1

INTEGRATION WITH CLAUDE AGENTS:
Add these commands to your agent workflow:
1. Regular polling: ./scripts/agent_poller.sh poll <your_name>
2. Task management: ./scripts/agent_poller.sh start <your_name> <task_id>
3. Status updates: ./scripts/agent_poller.sh status <your_name> <status>

EOF
}

# メイン処理
main() {
    local command="${1:-help}"
    
    case "$command" in
        "poll")
            quick_poll "$2"
            ;;
        "dashboard")
            show_dashboard "$2"
            ;;
        "tasks")
            check_my_tasks "$2"
            ;;
        "messages")
            check_my_messages "$2"
            ;;
        "start")
            start_task "$2" "$3"
            ;;
        "complete")
            complete_task "$2" "$3" "$4"
            ;;
        "status")
            update_my_status "$2" "$3" "$4"
            ;;
        "notify")
            notify_agent "$2" "$3" "$4" "$5" "$6"
            ;;
        "process-msg")
            process_message "$2"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# エラーハンドリング
trap 'log_error "Unexpected error occurred (line: $LINENO)"' ERR

# スクリプト実行
main "$@"