#!/bin/bash

# beehive.sh - Claude Multi-Agent Development System (Beehive) メインオーケストレーター
# 蜂の巣の管理、タスク実行、監視を行うメインスクリプト

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION_NAME="beehive"

# 色付きログ関数
log_info() {
    echo -e "\033[36m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

log_warning() {
    echo -e "\033[33m[WARNING]\033[0m $1"
}

# ヘルプ表示
show_help() {
    cat << 'EOF'
🐝 Claude Multi-Agent Development System (Beehive) 

USAGE:
    ./beehive.sh <command> [options]

COMMANDS:
    init [--force|-f]    Beehiveを初期化（tmuxセッション作成、Claude起動）
    inject-roles         各エージェントに役割を注入
    start-task <task>    Queen Beeにタスクを投入して実行開始
    task <command>       タスク管理システム操作（task help で詳細）
    status               各Beeの状態を確認
    logs [bee]           ログを表示（bee: queen|developer|qa）
    attach               tmuxセッションに接続
    remind [--bee bee]   コンテキストリマインダーを手動送信
    stop                 Beehiveを停止
    help                 このヘルプを表示

EXAMPLES:
    ./beehive.sh init --force
    ./beehive.sh inject-roles
    ./beehive.sh start-task "TODOアプリを作成してください"
    ./beehive.sh task list pending
    ./beehive.sh task stats
    ./beehive.sh status
    ./beehive.sh logs queen
    ./beehive.sh attach
    ./beehive.sh stop

NOTES:
    - 初回起動時: 'init' → 'inject-roles' → 'start-task' の順で実行
    - tmux (>= 3.0) と claude CLI が必要です
    - 各Beeは危険な権限モード (--dangerously-skip-permissions) で動作します

EOF
}

# セッション存在確認
check_session_exists() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_error "Beehiveセッションが存在しません"
        log_info "まず './beehive.sh init' を実行してください"
        return 1
    fi
    return 0
}

# init コマンド - Beehive初期化
cmd_init() {
    local force_init=false
    
    # オプション解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|-f)
                force_init=true
                shift
                ;;
            *)
                log_error "不明なオプション: $1"
                log_info "使用法: ./beehive.sh init [--force|-f]"
                return 1
                ;;
        esac
    done
    
    log_info "=== Beehive初期化開始 ==="
    
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        if [ "$force_init" = true ]; then
            log_info "強制初期化モード: 既存セッションを停止中..."
            tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
        else
            log_warning "既存のBeehiveセッションが見つかりました"
            read -p "既存セッションを終了して再作成しますか？ (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "初期化をキャンセルしました"
                log_info "強制初期化: './beehive.sh init --force'"
                return 0
            fi
        fi
    fi
    
    # init_hive.sh実行
    if [ -f "$SCRIPT_DIR/scripts/init_hive.sh" ]; then
        "$SCRIPT_DIR/scripts/init_hive.sh"
    else
        log_error "scripts/init_hive.sh が見つかりません"
        return 1
    fi
    
    log_success "Beehive初期化完了"
    log_info "次のステップ:"
    log_info "  1. ./beehive.sh inject-roles で役割を注入"
    log_info "  2. ./beehive.sh start-task \"タスク内容\" でタスクを開始"
}

# inject-roles コマンド - 役割注入
cmd_inject_roles() {
    check_session_exists || return 1
    
    log_info "各エージェントに役割を注入中..."
    
    if [ -f "$SCRIPT_DIR/scripts/inject_roles.sh" ]; then
        "$SCRIPT_DIR/scripts/inject_roles.sh" --all
    else
        log_error "scripts/inject_roles.sh が見つかりません"
        return 1
    fi
}

# start-task コマンド - タスク投入
cmd_start_task() {
    local task="${1:-}"
    
    if [ -z "$task" ]; then
        log_error "タスクが指定されていません"
        log_info "使用法: ./beehive.sh start-task \"タスク内容\""
        return 1
    fi
    
    check_session_exists || return 1
    
    log_info "タスクをQueen Beeに投入中: \"$task\""
    
    # タスク管理システムを使用してタスクを作成
    local task_id
    task_id=$("$SCRIPT_DIR/scripts/task_manager.sh" create "$task" "" "medium" "queen" 2>&1 | head -1)
    if [[ -n "$task_id" && "$task_id" =~ ^[0-9]+$ ]]; then
        log_success "タスクID $task_id で作成完了"
        
        # Queen BeeにSQLite経由でタスクを通知
        "$SCRIPT_DIR/scripts/task_manager.sh" message "system" "queen" "task_update" \
            "新しいタスクが割り当てられました" \
            "タスク「$task」(ID: $task_id) があなたに割り当てられました。このタスクを分析し、必要に応じてDeveloper BeeやQA Beeに作業を分担してください。詳細は task_manager.sh details $task_id で確認できます。" \
            "$task_id"
        
        # Queen Beeの状態をbusyに更新
        "$SCRIPT_DIR/scripts/task_manager.sh" bee-state "queen" "busy" "$task_id" "25"
        
        # CLI経由でタスク割り当て通知
        source "./scripts/send_keys_helper.sh"
        
        local task_message="## 🎯 新しいタスクが割り当てられました (ID: $task_id)
**タスク内容:** $task

詳細確認: \`./scripts/task_manager.sh details $task_id\`
このタスクを分析し、必要に応じて適切に分担してください。"

        assign_task "$SESSION_NAME" "0.0" "$task_message" "system" "${BEEHIVE_DRY_RUN:-false}"
        
        log_success "タスク投入完了 (ID: $task_id)"
        log_info "タスク詳細: './scripts/task_manager.sh details $task_id'"
        log_info "Queen Beeの応答を確認するには: './beehive.sh attach'"
        log_info "タスク状況確認: './scripts/task_manager.sh list pending'"
    else
        log_error "タスク作成に失敗しました"
        return 1
    fi
}

# status コマンド - 状態確認
cmd_status() {
    check_session_exists || return 1
    
    log_info "=== Beehive状態確認 ==="
    
    # セッション情報
    echo
    echo "📊 セッション情報:"
    tmux display-message -t "$SESSION_NAME" -p "  セッション: #S"
    tmux display-message -t "$SESSION_NAME" -p "  作成時間: #{session_created}"
    tmux display-message -t "$SESSION_NAME" -p "  ウィンドウ数: #{session_windows}"
    
    echo
    echo "🐝 Bee状態:"
    
    # 各ペインの状態
    local pane_count
    pane_count=$(tmux list-panes -t "$SESSION_NAME:0" | wc -l)
    echo "  アクティブペイン数: $pane_count/3"
    
    # ペイン詳細
    echo
    echo "📋 ペイン詳細:"
    tmux list-panes -t "$SESSION_NAME:0" -F "  ペイン#{pane_index}: #{pane_title} [#{pane_width}x#{pane_height}] #{?pane_active,(アクティブ),}"
    
    # データベースからBee状態とタスク情報を取得
    echo
    echo "🗄️  タスク管理状況:"
    if [[ -f "$SCRIPT_DIR/scripts/task_manager.sh" ]]; then
        # アクティブタスク数
        local task_count
        task_count=$("$SCRIPT_DIR/scripts/task_manager.sh" list pending | wc -l || echo "0")
        echo "  アクティブタスク数: $task_count"
        
        # Bee状態
        echo
        echo "🐝 Bee データベース状態:"
        "$SCRIPT_DIR/scripts/task_manager.sh" bees 2>/dev/null | while IFS='|' read -r bee_name status current_task workload _ _; do
            if [[ -n "$bee_name" && "$bee_name" != "bee_name" ]]; then
                echo "  $bee_name: $status (ワークロード: ${workload}%, タスク: ${current_task:-なし})"
            fi
        done
        
        # 最近のタスク
        echo
        echo "📋 最近のタスク:"
        "$SCRIPT_DIR/scripts/task_manager.sh" list all | head -5 2>/dev/null | while IFS='|' read -r task_id title status _ assigned_to _ _; do
            if [[ -n "$task_id" && "$task_id" != "task_id" ]]; then
                echo "  [$task_id] $title - $status (担当: ${assigned_to:-未割当})"
            fi
        done
    else
        echo "  タスク管理システム未利用"
    fi
    
    log_success "状態確認完了"
}

# logs コマンド - ログ表示
cmd_logs() {
    local bee="${1:-all}"
    
    check_session_exists || return 1
    
    case "$bee" in
        "queen"|"0")
            log_info "Queen Bee ログ（ペイン0）:"
            tmux capture-pane -t "$SESSION_NAME:0.0" -p
            ;;
        "developer"|"dev"|"1")
            log_info "Developer Bee ログ（ペイン1）:"
            tmux capture-pane -t "$SESSION_NAME:0.1" -p
            ;;
        "qa"|"2")
            log_info "QA Bee ログ（ペイン2）:"
            tmux capture-pane -t "$SESSION_NAME:0.2" -p
            ;;
        "all"|*)
            log_info "=== 全Bee ログ ==="
            echo
            echo "🐝 Queen Bee (ペイン0):"
            tmux capture-pane -t "$SESSION_NAME:0.0" -p | tail -10
            echo
            echo "💻 Developer Bee (ペイン1):"
            tmux capture-pane -t "$SESSION_NAME:0.1" -p | tail -10
            echo
            echo "🔍 QA Bee (ペイン2):"
            tmux capture-pane -t "$SESSION_NAME:0.2" -p | tail -10
            ;;
    esac
}

# attach コマンド - セッション接続
cmd_attach() {
    check_session_exists || return 1
    
    log_info "Beehiveセッションに接続中..."
    log_info "終了するには Ctrl+B → D を押してください"
    sleep 1
    
    exec tmux attach-session -t "$SESSION_NAME"
}

# remind コマンド - リマインダー送信
cmd_remind() {
    local target_bee=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --bee)
                target_bee="$2"
                shift 2
                ;;
            *)
                log_error "不明なオプション: $1"
                return 1
                ;;
        esac
    done
    
    check_session_exists || return 1
    
    # TODO: 実際のリマインダー機能は Issue #5 で実装
    log_warning "リマインダー機能は未実装です（Issue #5で実装予定）"
    log_info "暫定的に手動リマインダーを送信します"
    
    if [ -n "$target_bee" ]; then
        source "./scripts/send_keys_helper.sh"
        
        case "$target_bee" in
            "queen"|"0")
                inject_role "$SESSION_NAME" "0.0" "🔔 [ROLE REMINDER] あなたはQueen Beeです。タスクの計画・分解・指示を担当してください。" "${BEEHIVE_DRY_RUN:-false}"
                ;;
            "developer"|"dev"|"1")
                inject_role "$SESSION_NAME" "0.1" "🔔 [ROLE REMINDER] あなたはDeveloper Beeです。コードの実装を担当してください。" "${BEEHIVE_DRY_RUN:-false}"
                ;;
            "qa"|"2")
                inject_role "$SESSION_NAME" "0.2" "🔔 [ROLE REMINDER] あなたはQA Beeです。テストと品質保証を担当してください。" "${BEEHIVE_DRY_RUN:-false}"
                ;;
        esac
        log_success "$target_bee にリマインダーを送信しました"
    else
        # 全Beeにリマインダー
        cmd_remind --bee queen
        cmd_remind --bee developer
        cmd_remind --bee qa
        log_success "全Beeにリマインダーを送信しました"
    fi
}

# task コマンド - タスク管理システム操作
cmd_task() {
    if [[ ! -f "$SCRIPT_DIR/scripts/task_manager.sh" ]]; then
        log_error "タスク管理システムが見つかりません"
        log_info "scripts/task_manager.sh が存在しません"
        return 1
    fi
    
    # 引数をそのままタスク管理スクリプトに渡す
    "$SCRIPT_DIR/scripts/task_manager.sh" "$@"
}

# stop コマンド - 停止
cmd_stop() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_info "Beehiveセッションは既に停止しています"
        return 0
    fi
    
    log_info "Beehiveを停止中..."
    
    # セッション終了前の確認
    read -p "本当にBeehiveを停止しますか？ 進行中の作業が失われる可能性があります (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "停止をキャンセルしました"
        return 0
    fi
    
    tmux kill-session -t "$SESSION_NAME"
    
    log_success "Beehive停止完了"
}

# メイン処理
main() {
    local command="${1:-help}"
    
    case "$command" in
        "init")
            shift
            cmd_init "$@"
            ;;
        "inject-roles")
            cmd_inject_roles
            ;;
        "start-task")
            shift
            cmd_start_task "$@"
            ;;
        "task")
            shift
            cmd_task "$@"
            ;;
        "status")
            cmd_status
            ;;
        "logs")
            shift
            cmd_logs "$@"
            ;;
        "attach")
            cmd_attach
            ;;
        "remind")
            shift
            cmd_remind "$@"
            ;;
        "stop")
            cmd_stop
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "不明なコマンド: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# エラーハンドリング
trap 'log_error "予期しないエラーが発生しました（行: $LINENO）"' ERR

# スクリプト実行
main "$@"