#!/bin/bash

# beehive.sh - Claude Multi-Agent Development System (Beehive) メインオーケストレーター
# 蜂の巣の管理、タスク実行、監視を行うメインスクリプト

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
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
    daemon <command>     リマインダーデーモン管理（daemon help で詳細）
    web <command>        Webダッシュボード管理（web help で詳細）
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
    ./beehive.sh web start
    ./beehive.sh web status
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
    
    # sender CLI経由でQueen Beeに直接タスクを送信（シンプル版）
    source "./scripts/send_keys_helper.sh"
    
    local task_message="## 🎯 新しいタスクが割り当てられました

**タスク内容:** $task

このタスクを分析し、必要に応じてDeveloper BeeやQA Beeに作業を分担してください。
完了したら進捗を報告してください。"

    assign_task "$SESSION_NAME" "0" "$task_message" "system" "false"
    
    log_success "タスク投入完了"
    log_info "Queen Beeの応答を確認するには: './beehive.sh attach'"
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
            log_info "Queen Bee ログ（ウィンドウ0）:"
            tmux capture-pane -t "$SESSION_NAME:0" -p
            ;;
        "developer"|"dev"|"1")
            log_info "Developer Bee ログ（ウィンドウ1）:"
            tmux capture-pane -t "$SESSION_NAME:1" -p
            ;;
        "qa"|"2")
            log_info "QA Bee ログ（ウィンドウ2）:"
            tmux capture-pane -t "$SESSION_NAME:2" -p
            ;;
        "analyst"|"3")
            log_info "Analyst Bee ログ（ウィンドウ3）:"
            tmux capture-pane -t "$SESSION_NAME:3" -p
            ;;
        "all"|*)
            log_info "=== 全Bee ログ ==="
            echo
            echo "🐝 Queen Bee (ウィンドウ0):"
            tmux capture-pane -t "$SESSION_NAME:0" -p | tail -10
            echo
            echo "💻 Developer Bee (ウィンドウ1):"
            tmux capture-pane -t "$SESSION_NAME:1" -p | tail -10
            echo
            echo "🔍 QA Bee (ウィンドウ2):"
            tmux capture-pane -t "$SESSION_NAME:2" -p | tail -10
            echo
            echo "📊 Analyst Bee (ウィンドウ3):"
            tmux capture-pane -t "$SESSION_NAME:3" -p | tail -10
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
    
    log_info "コンテキストリマインダーを送信します"
    
    if [ -n "$target_bee" ]; then
        # 特定のBeeにリマインダー送信
        if python -m memory.context_manager --remind-bee "$target_bee"; then
            log_success "$target_bee にリマインダーを送信しました"
        else
            log_error "$target_bee へのリマインダー送信に失敗しました"
            return 1
        fi
    else
        # 全Beeにリマインダー送信
        if python -m memory.context_manager --remind-all; then
            log_success "全Beeにリマインダーを送信しました"
        else
            log_error "リマインダー送信に失敗しました"
            return 1
        fi
    fi
}

# daemon コマンド - リマインダーデーモン管理
cmd_daemon() {
    local daemon_script="$PROJECT_ROOT/scripts/reminder_daemon.sh"
    
    if [[ ! -f "$daemon_script" ]]; then
        log_error "リマインダーデーモンスクリプトが見つかりません: $daemon_script"
        return 1
    fi
    
    # reminder_daemon.shに全ての引数を渡す
    "$daemon_script" "$@"
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

# web コマンド - Webダッシュボード管理
cmd_web() {
    local web_command="${1:-help}"
    
    case "$web_command" in
        "start")
            cmd_web_start
            ;;
        "stop")
            cmd_web_stop
            ;;
        "status")
            cmd_web_status
            ;;
        "logs")
            cmd_web_logs
            ;;
        "help"|*)
            cmd_web_help
            ;;
    esac
}

# Webダッシュボード開始
cmd_web_start() {
    log_info "=== Webダッシュボード開始 ==="
    
    # バックエンド開始
    log_info "バックエンドサーバーを開始中..."
    cd "$SCRIPT_DIR/web/backend"
    
    if [ ! -f "pyproject.toml" ]; then
        log_error "バックエンド設定ファイルが見つかりません"
        return 1
    fi
    
    # バックグラウンドでバックエンド起動（uvを使用）
    nohup uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$SCRIPT_DIR/logs/web-backend.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/logs/web-backend.pid"
    
    sleep 2
    
    # フロントエンド開始
    log_info "フロントエンドサーバーを開始中..."
    cd "$SCRIPT_DIR/web/frontend"
    
    if [ ! -f "package.json" ]; then
        log_error "フロントエンド設定ファイルが見つかりません"
        return 1
    fi
    
    # フロントエンド依存関係インストール（初回のみ）
    if [ ! -d "node_modules" ]; then
        log_info "依存関係をインストール中..."
        npm install
    fi
    
    # バックグラウンドでフロントエンド起動
    nohup npm run start > "$SCRIPT_DIR/logs/web-frontend.log" 2>&1 &
    echo $! > "$SCRIPT_DIR/logs/web-frontend.pid"
    
    log_success "Webダッシュボード開始完了"
    log_info "アクセス先: http://localhost:3000"
    log_info "API: http://localhost:8000"
    log_info "停止するには: ./beehive.sh web stop"
}

# Webダッシュボード停止
cmd_web_stop() {
    log_info "Webダッシュボードを停止中..."
    
    # バックエンド停止
    if [ -f "$SCRIPT_DIR/logs/web-backend.pid" ]; then
        local backend_pid
        backend_pid=$(cat "$SCRIPT_DIR/logs/web-backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            kill "$backend_pid"
            log_info "バックエンドサーバーを停止しました"
        fi
        rm -f "$SCRIPT_DIR/logs/web-backend.pid"
    fi
    
    # フロントエンド停止
    if [ -f "$SCRIPT_DIR/logs/web-frontend.pid" ]; then
        local frontend_pid
        frontend_pid=$(cat "$SCRIPT_DIR/logs/web-frontend.pid")
        if kill -0 "$frontend_pid" 2>/dev/null; then
            kill "$frontend_pid"
            log_info "フロントエンドサーバーを停止しました"
        fi
        rm -f "$SCRIPT_DIR/logs/web-frontend.pid"
    fi
    
    log_success "Webダッシュボード停止完了"
}

# Webダッシュボード状態確認
cmd_web_status() {
    log_info "=== Webダッシュボード状態 ==="
    
    local backend_running=false
    local frontend_running=false
    
    # バックエンド状態
    if [ -f "$SCRIPT_DIR/logs/web-backend.pid" ]; then
        local backend_pid
        backend_pid=$(cat "$SCRIPT_DIR/logs/web-backend.pid")
        if kill -0 "$backend_pid" 2>/dev/null; then
            echo "🟢 バックエンド: 実行中 (PID: $backend_pid, ポート: 8000)"
            backend_running=true
        else
            echo "🔴 バックエンド: 停止中"
            rm -f "$SCRIPT_DIR/logs/web-backend.pid"
        fi
    else
        echo "🔴 バックエンド: 停止中"
    fi
    
    # フロントエンド状態
    if [ -f "$SCRIPT_DIR/logs/web-frontend.pid" ]; then
        local frontend_pid
        frontend_pid=$(cat "$SCRIPT_DIR/logs/web-frontend.pid")
        if kill -0 "$frontend_pid" 2>/dev/null; then
            echo "🟢 フロントエンド: 実行中 (PID: $frontend_pid, ポート: 3000)"
            frontend_running=true
        else
            echo "🔴 フロントエンド: 停止中"
            rm -f "$SCRIPT_DIR/logs/web-frontend.pid"
        fi
    else
        echo "🔴 フロントエンド: 停止中"
    fi
    
    echo
    if [ "$backend_running" = true ] && [ "$frontend_running" = true ]; then
        echo "✅ Webダッシュボードは正常に動作中です"
        echo "   アクセス先: http://localhost:3000"
    elif [ "$backend_running" = true ] || [ "$frontend_running" = true ]; then
        echo "⚠️  Webダッシュボードは部分的に動作中です"
    else
        echo "❌ Webダッシュボードは停止中です"
        echo "   開始するには: ./beehive.sh web start"
    fi
}

# Webダッシュボードログ表示
cmd_web_logs() {
    log_info "=== Webダッシュボードログ ==="
    
    echo
    echo "🔧 バックエンドログ:"
    if [ -f "$SCRIPT_DIR/logs/web-backend.log" ]; then
        tail -20 "$SCRIPT_DIR/logs/web-backend.log"
    else
        echo "ログファイルが見つかりません"
    fi
    
    echo
    echo "🌐 フロントエンドログ:"
    if [ -f "$SCRIPT_DIR/logs/web-frontend.log" ]; then
        tail -20 "$SCRIPT_DIR/logs/web-frontend.log"
    else
        echo "ログファイルが見つかりません"
    fi
}

# Webダッシュボードヘルプ
cmd_web_help() {
    cat << 'EOF'
🌐 Webダッシュボード管理コマンド

USAGE:
    ./beehive.sh web <command>

COMMANDS:
    start     Webダッシュボードを開始（バックエンド + フロントエンド）
    stop      Webダッシュボードを停止
    status    Webダッシュボードの状態を確認
    logs      Webダッシュボードのログを表示
    help      このヘルプを表示

EXAMPLES:
    ./beehive.sh web start    # ダッシュボード開始
    ./beehive.sh web status   # 状態確認
    ./beehive.sh web logs     # ログ確認
    ./beehive.sh web stop     # ダッシュボード停止

PORTS:
    フロントエンド: http://localhost:3000
    バックエンドAPI: http://localhost:8000
    WebSocket: ws://localhost:8000/ws/

NOTES:
    - BeehiveシステムがinitされてからWebダッシュボードを起動してください
    - フロントエンドは初回起動時に依存関係を自動インストールします
    - ログファイルは logs/ ディレクトリに保存されます

EOF
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
        "daemon")
            shift
            cmd_daemon "$@"
            ;;
        "web")
            shift
            cmd_web "$@"
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