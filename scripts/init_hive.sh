#!/bin/bash

# init_hive.sh - Beehive起動スクリプト
# tmuxセッション内でClaude CLIインスタンスを起動し、各エージェントを待機状態にします

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェック中..."
    
    # tmuxの確認
    if ! command -v tmux &> /dev/null; then
        log_error "tmuxがインストールされていません"
        exit 1
    fi
    
    # tmuxバージョンチェック
    local tmux_version=$(tmux -V | cut -d' ' -f2)
    log_info "tmux バージョン: $tmux_version"
    
    # Claude CLIの確認
    if ! command -v claude &> /dev/null; then
        log_error "claude CLIがインストールされていません"
        exit 1
    fi
    
    # 危険な権限の確認
    if ! claude --dangerously-skip-permissions --help &> /dev/null; then
        log_error "claude --dangerously-skip-permissions が利用できません"
        exit 1
    fi
    
    log_success "全ての前提条件をクリア"
}

# 既存セッションの確認と終了
cleanup_existing_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_warning "既存のBeehiveセッション「$SESSION_NAME」を発見"
        log_info "既存セッションを終了中..."
        tmux kill-session -t "$SESSION_NAME"
        sleep 2
    fi
}

# tmuxセッション作成
create_tmux_session() {
    log_info "tmuxセッション「$SESSION_NAME」を作成中..."
    
    # 新しいセッション作成（デタッチ状態で）
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT"
    
    # セッション設定
    tmux set-option -t "$SESSION_NAME" status-position top
    tmux set-option -t "$SESSION_NAME" status-style "bg=colour236,fg=colour255"
    tmux set-option -t "$SESSION_NAME" status-left "#[bg=colour27,fg=colour255] 🐝 BEEHIVE #[default] "
    tmux set-option -t "$SESSION_NAME" status-left-length 20
    tmux set-option -t "$SESSION_NAME" status-right "#[fg=colour255]%Y-%m-%d %H:%M#[default] "
    
    log_success "tmuxセッション作成完了"
}

# 3つのペイン作成
create_panes() {
    log_info "Beeペインを作成中..."
    
    # 元のウィンドウをQueen用に設定
    tmux rename-window -t "$SESSION_NAME:0" "hive"
    
    # 2つ目のペインを作成（Developer用）
    tmux split-window -t "$SESSION_NAME:0" -v -c "$PROJECT_ROOT/workspaces/developer"
    
    # 3つ目のペインを作成（QA用）
    tmux split-window -t "$SESSION_NAME:0" -h -c "$PROJECT_ROOT/workspaces/qa"
    
    # レイアウト調整（Queen上部50%、Developer左下25%、QA右下25%）
    tmux select-layout -t "$SESSION_NAME:0" main-horizontal
    
    log_success "3つのペイン作成完了"
}

# ペインタイトル設定
set_pane_titles() {
    log_info "ペインタイトルを設定中..."
    
    # ペインタイトル表示を有効化
    tmux set-option -t "$SESSION_NAME" pane-border-status top
    tmux set-option -t "$SESSION_NAME" pane-border-format "#{?pane_active,#[bg=colour27]#[fg=colour255],#[bg=colour236]#[fg=colour255]} #{pane_title} #{?pane_active,#[default],#[default]}"
    
    # 各ペインにタイトル設定
    tmux select-pane -t "$SESSION_NAME:0.0" -T "[QUEEN] Planning & Coordination"
    tmux select-pane -t "$SESSION_NAME:0.1" -T "[DEVELOPER] Implementation"
    tmux select-pane -t "$SESSION_NAME:0.2" -T "[QA] Testing & Quality"
    
    log_success "ペインタイトル設定完了"
}

# Claude CLIインスタンス起動
start_claude_instances() {
    log_info "Claude CLIインスタンスを起動中..."
    
    # Queen Bee起動
    log_info "Queen Beeを起動中（ペイン0）..."
    tmux send-keys -t "$SESSION_NAME:0.0" "cd $PROJECT_ROOT/workspaces/queen" Enter
    tmux send-keys -t "$SESSION_NAME:0.0" "claude --dangerously-skip-permissions" Enter
    sleep 2
    
    # Developer Bee起動
    log_info "Developer Beeを起動中（ペイン1）..."
    tmux send-keys -t "$SESSION_NAME:0.1" "cd $PROJECT_ROOT/workspaces/developer" Enter
    tmux send-keys -t "$SESSION_NAME:0.1" "claude --dangerously-skip-permissions" Enter
    sleep 2
    
    # QA Bee起動
    log_info "QA Beeを起動中（ペイン2）..."
    tmux send-keys -t "$SESSION_NAME:0.2" "cd $PROJECT_ROOT/workspaces/qa" Enter
    tmux send-keys -t "$SESSION_NAME:0.2" "claude --dangerously-skip-permissions" Enter
    sleep 2
    
    log_success "全てのClaude CLIインスタンス起動完了"
}

# 起動確認
verify_startup() {
    log_info "起動状態を確認中..."
    
    # セッション存在確認
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_error "tmuxセッションが存在しません"
        return 1
    fi
    
    # ペイン数確認
    local pane_count=$(tmux list-panes -t "$SESSION_NAME:0" | wc -l)
    if [ "$pane_count" -ne 3 ]; then
        log_error "ペイン数が不正です（期待値: 3, 実際: $pane_count）"
        return 1
    fi
    
    log_success "Beehive起動確認完了"
    log_info "次のステップ："
    log_info "  1. ./beehive.sh attach でセッションに接続"
    log_info "  2. 各ペインでClaudeが起動していることを確認"
    log_info "  3. ./scripts/inject_roles.sh で役割を注入（未実装）"
    
    return 0
}

# メイン処理
main() {
    log_info "=== Beehive初期化開始 ==="
    
    check_prerequisites
    cleanup_existing_session
    create_tmux_session
    create_panes
    set_pane_titles
    start_claude_instances
    
    if verify_startup; then
        log_success "=== Beehive初期化完了 ==="
        log_info "tmux attach-session -t $SESSION_NAME でセッションに接続できます"
    else
        log_error "=== 初期化中にエラーが発生しました ==="
        exit 1
    fi
}

# エラーハンドリング
trap 'log_error "予期しないエラーが発生しました（行: $LINENO）"' ERR

# スクリプト実行
main "$@"