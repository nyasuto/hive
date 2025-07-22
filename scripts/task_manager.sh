#!/bin/bash

# task_manager.sh - Task Management System for Claude Multi-Agent System (Beehive)
# Handles task creation, assignment, status updates, and inter-bee communication
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_ROOT/hive/hive_memory.db"
SCHEMA_PATH="$PROJECT_ROOT/hive/schema.sql"

# 色付きログ関数
log_info() { echo -e "\033[36m[TASK]  \033[0m $1"; }
log_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }
log_warning() { echo -e "\033[33m[WARNING]\033[0m $1"; }

# データベース初期化
init_database() {
    log_info "Initializing task management database..."
    
    if [[ ! -f "$SCHEMA_PATH" ]]; then
        log_error "Schema file not found: $SCHEMA_PATH"
        return 1
    fi
    
    # データベースディレクトリ作成
    mkdir -p "$(dirname "$DB_PATH")"
    
    # スキーマ実行
    if sqlite3 "$DB_PATH" < "$SCHEMA_PATH"; then
        log_success "Database initialized successfully"
        return 0
    else
        log_error "Database initialization failed"
        return 1
    fi
}

# データベース存在確認
check_database() {
    if [[ ! -f "$DB_PATH" ]]; then
        log_warning "Database not found, initializing..."
        init_database
        return $?
    fi
    return 0
}

# タスク作成
create_task() {
    local title="$1"
    local description="${2:-}"
    local priority="${3:-medium}"
    local assigned_to="${4:-}"
    local due_date="${5:-}"
    
    check_database || return 1
    
    log_info "Creating task: $title"
    
    # SQLクエリで特殊文字をエスケープ
    local escaped_title
    local escaped_description
    escaped_title=$(printf '%s\n' "$title" | sed "s/'/''/g")
    escaped_description=$(printf '%s\n' "$description" | sed "s/'/''/g")
    
    local task_id
    task_id=$(sqlite3 "$DB_PATH" "
        INSERT INTO tasks (title, description, priority, assigned_to, due_date)
        VALUES ('$escaped_title', '$escaped_description', '$priority', 
                $(if [[ -n "$assigned_to" ]]; then echo "'$assigned_to'"; else echo "NULL"; fi),
                $(if [[ -n "$due_date" ]]; then echo "'$due_date'"; else echo "NULL"; fi))
        RETURNING task_id;
    ")
    
    if [[ -n "$task_id" ]]; then
        # Task IDを先に出力（beehive.shから取得するため）
        echo "$task_id"
        
        log_success "Task created with ID: $task_id" >&2
        
        # タスク作成をアクティビティログに記録
        log_task_activity "$task_id" "system" "created" "Task created: $title" 2>/dev/null || true
        
        # 担当者が指定されている場合は通知メッセージを送信
        if [[ -n "$assigned_to" ]]; then
            send_message "system" "$assigned_to" "task_update" "新しいタスクが割り当てられました" \
                "タスク「$title」があなたに割り当てられました。詳細を確認してください。" "$task_id" 2>/dev/null || true
        fi
        
        return 0
    else
        log_error "Failed to create task"
        return 1
    fi
}

# タスク状態更新
update_task_status() {
    local task_id="$1"
    local new_status="$2"
    local bee_name="${3:-system}"
    local notes="${4:-}"
    
    check_database || return 1
    
    log_info "Updating task $task_id status to: $new_status"
    
    # 現在のステータスを取得
    local old_status
    old_status=$(sqlite3 "$DB_PATH" "SELECT status FROM tasks WHERE task_id = $task_id;")
    
    if [[ -z "$old_status" ]]; then
        log_error "Task not found: $task_id"
        return 1
    fi
    
    # ステータス更新
    local update_fields="status = '$new_status', updated_at = CURRENT_TIMESTAMP"
    
    # 特定ステータスの場合は追加フィールドを更新
    case "$new_status" in
        "in_progress")
            update_fields="$update_fields, started_at = CURRENT_TIMESTAMP"
            ;;
        "completed"|"failed"|"cancelled")
            update_fields="$update_fields, completed_at = CURRENT_TIMESTAMP"
            ;;
    esac
    
    sqlite3 "$DB_PATH" "
        UPDATE tasks 
        SET $update_fields
        WHERE task_id = $task_id;
    "
    
    log_task_activity "$task_id" "$bee_name" "status_update" \
        "Status changed from '$old_status' to '$new_status'" "$notes"
    
    log_success "Task $task_id status updated: $old_status -> $new_status"
    
    # 完了時は担当者に通知
    if [[ "$new_status" == "completed" ]]; then
        local assigned_to
        assigned_to=$(sqlite3 "$DB_PATH" "SELECT assigned_to FROM tasks WHERE task_id = $task_id;")
        if [[ -n "$assigned_to" && "$assigned_to" != "NULL" ]]; then
            send_message "system" "$assigned_to" "task_update" "タスク完了確認" \
                "タスクが完了しました。確認をお願いします。" "$task_id"
        fi
    fi
}

# タスク割り当て
assign_task() {
    local task_id="$1"
    local assigned_to="$2"
    local assigned_by="${3:-system}"
    local assignment_type="${4:-primary}"
    
    check_database || return 1
    
    log_info "Assigning task $task_id to $assigned_to"
    
    # タスクの割り当てを更新
    sqlite3 "$DB_PATH" "
        UPDATE tasks 
        SET assigned_to = '$assigned_to', updated_at = CURRENT_TIMESTAMP
        WHERE task_id = $task_id;
        
        INSERT INTO task_assignments (task_id, assigned_to, assigned_by, assignment_type)
        VALUES ($task_id, '$assigned_to', '$assigned_by', '$assignment_type');
    "
    
    log_task_activity "$task_id" "$assigned_by" "assignment" \
        "Task assigned to $assigned_to" "Assignment type: $assignment_type"
    
    # 担当者に通知
    local task_title
    task_title=$(sqlite3 "$DB_PATH" "SELECT title FROM tasks WHERE task_id = $task_id;")
    
    send_message "$assigned_by" "$assigned_to" "task_update" "新しいタスクの割り当て" \
        "「$task_title」があなたに割り当てられました。作業を開始してください。" "$task_id"
    
    log_success "Task $task_id assigned to $assigned_to"
}

# Bee状態更新
update_bee_state() {
    local bee_name="$1"
    local status="${2:-idle}"
    local current_task_id="${3:-}"
    local workload_score="${4:-0}"
    
    check_database || return 1
    
    log_info "Updating $bee_name state: $status"
    
    sqlite3 "$DB_PATH" "
        UPDATE bee_states 
        SET status = '$status',
            current_task_id = $(if [[ -n "$current_task_id" ]]; then echo "$current_task_id"; else echo "NULL"; fi),
            workload_score = $workload_score,
            last_heartbeat = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE bee_name = '$bee_name';
    "
    
    log_success "Bee state updated: $bee_name -> $status"
}

# メッセージ送信
send_message() {
    local from_bee="$1"
    local to_bee="$2"
    local message_type="${3:-info}"
    local subject="$4"
    local content="$5"
    local task_id="${6:-}"
    local priority="${7:-normal}"
    
    check_database || return 1
    
    log_info "Sending message from $from_bee to $to_bee: $subject"
    
    # 特殊文字エスケープ
    local escaped_subject
    local escaped_content
    escaped_subject=$(printf '%s\n' "$subject" | sed "s/'/''/g")
    escaped_content=$(printf '%s\n' "$content" | sed "s/'/''/g")
    
    sqlite3 "$DB_PATH" "
        INSERT INTO bee_messages (from_bee, to_bee, message_type, subject, content, task_id, priority)
        VALUES ('$from_bee', '$to_bee', '$message_type', '$escaped_subject', '$escaped_content',
                $(if [[ -n "$task_id" ]]; then echo "$task_id"; else echo "NULL"; fi), '$priority');
    "
    
    log_success "Message sent to $to_bee"
}

# アクティビティログ記録
log_task_activity() {
    local task_id="$1"
    local bee_name="$2"
    local activity_type="$3"
    local description="$4"
    local metadata="${5:-}"
    
    check_database || return 1
    
    # 特殊文字エスケープ
    local escaped_description
    local escaped_metadata
    escaped_description=$(printf '%s\n' "$description" | sed "s/'/''/g")
    escaped_metadata=$(printf '%s\n' "$metadata" | sed "s/'/''/g")
    
    sqlite3 "$DB_PATH" "
        INSERT INTO task_activity (task_id, bee_name, activity_type, description, metadata)
        VALUES ($task_id, '$bee_name', '$activity_type', '$escaped_description', 
                $(if [[ -n "$metadata" ]]; then echo "'$escaped_metadata'"; else echo "NULL"; fi));
    "
}

# 未処理メッセージ取得
get_pending_messages() {
    local bee_name="${1:-all}"
    
    check_database || return 1
    
    local where_clause=""
    if [[ "$bee_name" != "all" ]]; then
        where_clause="AND to_bee IN ('$bee_name', 'all')"
    fi
    
    sqlite3 "$DB_PATH" "
        SELECT message_id, from_bee, to_bee, message_type, subject, content, 
               task_id, priority, created_at
        FROM bee_messages 
        WHERE processed = FALSE 
        $where_clause
        ORDER BY priority DESC, created_at ASC;
    "
}

# メッセージ処理済みマーク
mark_message_processed() {
    local message_id="$1"
    
    check_database || return 1
    
    sqlite3 "$DB_PATH" "
        UPDATE bee_messages 
        SET processed = TRUE, processed_at = CURRENT_TIMESTAMP
        WHERE message_id = $message_id;
    "
}

# タスク一覧取得
list_tasks() {
    local status_filter="${1:-all}"
    local assigned_to_filter="${2:-all}"
    
    check_database || return 1
    
    local where_conditions=""
    
    if [[ "$status_filter" != "all" ]]; then
        where_conditions="WHERE status = '$status_filter'"
    fi
    
    if [[ "$assigned_to_filter" != "all" ]]; then
        if [[ -n "$where_conditions" ]]; then
            where_conditions="$where_conditions AND assigned_to = '$assigned_to_filter'"
        else
            where_conditions="WHERE assigned_to = '$assigned_to_filter'"
        fi
    fi
    
    sqlite3 "$DB_PATH" "
        SELECT task_id, title, status, priority, assigned_to, 
               created_at, updated_at
        FROM tasks 
        $where_conditions
        ORDER BY priority DESC, created_at DESC;
    "
}

# タスク詳細取得
get_task_details() {
    local task_id="$1"
    
    check_database || return 1
    
    sqlite3 "$DB_PATH" "
        SELECT task_id, title, description, status, priority, assigned_to,
               created_at, updated_at, started_at, completed_at, due_date,
               estimated_hours, actual_hours, tags, metadata, created_by
        FROM tasks 
        WHERE task_id = $task_id;
    "
}

# Bee状態一覧
list_bee_states() {
    check_database || return 1
    
    sqlite3 "$DB_PATH" "
        SELECT bee_name, status, current_task_id, workload_score, 
               performance_score, last_heartbeat
        FROM bee_states
        ORDER BY bee_name;
    "
}

# タスク統計
get_task_stats() {
    check_database || return 1
    
    echo "=== Task Statistics ==="
    echo
    
    echo "📊 Status Distribution:"
    sqlite3 "$DB_PATH" "
        SELECT status, COUNT(*) as count
        FROM tasks 
        GROUP BY status 
        ORDER BY count DESC;
    "
    
    echo
    echo "🐝 Bee Workload:"
    sqlite3 "$DB_PATH" "
        SELECT 
            COALESCE(assigned_to, 'unassigned') as bee,
            COUNT(*) as active_tasks
        FROM tasks 
        WHERE status IN ('pending', 'in_progress')
        GROUP BY assigned_to
        ORDER BY active_tasks DESC;
    "
    
    echo
    echo "📈 Recent Activity:"
    sqlite3 "$DB_PATH" "
        SELECT DATE(created_at) as date, COUNT(*) as tasks_created
        FROM tasks 
        WHERE created_at >= date('now', '-7 days')
        GROUP BY DATE(created_at)
        ORDER BY date DESC;
    "
}

# ヘルプ表示
show_help() {
    cat << 'EOF'
🐝 Task Manager for Claude Multi-Agent System (Beehive)

USAGE:
    ./scripts/task_manager.sh <command> [options]

COMMANDS:
    init                           Initialize database
    create <title> [desc] [priority] [assignee] [due]
                                  Create new task
    assign <task_id> <bee> [type] Assign task to bee
    status <task_id> <status> [bee] [notes]
                                  Update task status  
    message <from> <to> <type> <subject> <content> [task_id]
                                  Send message between bees
    bee-state <bee> <status> [task_id] [workload]
                                  Update bee state
    list [status] [assignee]      List tasks
    details <task_id>             Show task details
    messages [bee]                Get pending messages
    processed <message_id>        Mark message as processed
    bees                          List bee states
    stats                         Show task statistics
    help                          Show this help

EXAMPLES:
    ./scripts/task_manager.sh create "TODOアプリ作成" "Reactでシンプルなアプリを作る" high developer
    ./scripts/task_manager.sh assign 1 developer primary
    ./scripts/task_manager.sh status 1 in_progress developer "作業開始しました"
    ./scripts/task_manager.sh list pending developer
    ./scripts/task_manager.sh messages queen
    ./scripts/task_manager.sh stats

BEE NAMES: queen, developer, qa
TASK STATUSES: pending, in_progress, completed, failed, cancelled
PRIORITIES: low, medium, high, critical

EOF
}

# メイン処理
main() {
    local command="${1:-help}"
    
    case "$command" in
        "init")
            init_database
            ;;
        "create")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: create <title> [description] [priority] [assignee] [due_date]"
                exit 1
            fi
            create_task "$2" "${3:-}" "${4:-medium}" "${5:-}" "${6:-}"
            ;;
        "assign")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: assign <task_id> <bee_name> [assignment_type]"
                exit 1
            fi
            assign_task "$2" "$3" "system" "${4:-primary}"
            ;;
        "status")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: status <task_id> <status> [bee_name] [notes]"
                exit 1
            fi
            update_task_status "$2" "$3" "${4:-system}" "${5:-}"
            ;;
        "message")
            if [[ $# -lt 6 ]]; then
                log_error "Usage: message <from> <to> <type> <subject> <content> [task_id]"
                exit 1
            fi
            send_message "$2" "$3" "$4" "$5" "$6" "${7:-}"
            ;;
        "bee-state")
            if [[ $# -lt 3 ]]; then
                log_error "Usage: bee-state <bee_name> <status> [current_task_id] [workload_score]"
                exit 1
            fi
            update_bee_state "$2" "$3" "${4:-}" "${5:-0}"
            ;;
        "list")
            list_tasks "${2:-all}" "${3:-all}"
            ;;
        "details")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: details <task_id>"
                exit 1
            fi
            get_task_details "$2"
            ;;
        "messages")
            get_pending_messages "${2:-all}"
            ;;
        "processed")
            if [[ $# -lt 2 ]]; then
                log_error "Usage: processed <message_id>"
                exit 1
            fi
            mark_message_processed "$2"
            ;;
        "bees")
            list_bee_states
            ;;
        "stats")
            get_task_stats
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