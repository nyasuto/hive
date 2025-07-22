#!/bin/bash

# init_hive.sh - Beehive startup script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_NAME="beehive"

log_info() { echo -e "\033[36m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }
log_warning() { echo -e "\033[33m[WARNING]\033[0m $1"; }

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v tmux &> /dev/null; then
        log_error "tmux is not installed"
        exit 1
    fi
    
    local tmux_version
    tmux_version=$(tmux -V | cut -d' ' -f2)
    log_info "tmux version: $tmux_version"
    
    if ! command -v claude &> /dev/null; then
        log_error "claude CLI is not installed"
        exit 1
    fi
    
    if ! claude --dangerously-skip-permissions --help &> /dev/null; then
        log_error "claude --dangerously-skip-permissions is not available"
        exit 1
    fi
    
    log_success "All prerequisites satisfied"
}

cleanup_existing_session() {
    if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_warning "Found existing Beehive session: $SESSION_NAME"
        log_info "Terminating existing session..."
        tmux kill-session -t "$SESSION_NAME"
        sleep 2
    fi
}

create_tmux_session() {
    log_info "Creating tmux session: $SESSION_NAME"
    
    tmux new-session -d -s "$SESSION_NAME" -c "$PROJECT_ROOT"
    tmux set-option -t "$SESSION_NAME" status-position top
    tmux set-option -t "$SESSION_NAME" status-style "bg=colour236,fg=colour255"
    tmux set-option -t "$SESSION_NAME" status-left "#[bg=colour27,fg=colour255] 🐝 BEEHIVE #[default] "
    tmux set-option -t "$SESSION_NAME" status-left-length 20
    tmux set-option -t "$SESSION_NAME" status-right "#[fg=colour255]%Y-%m-%d %H:%M#[default] "
    
    log_success "tmux session created successfully"
}

create_windows() {
    log_info "Creating Bee windows (1 bee per window)..."
    
    # Window 0: Queen Bee (プロジェクトルートで起動)
    tmux rename-window -t "$SESSION_NAME:0" "queen"
    
    # Window 1: Developer Bee (プロジェクトルートで起動)
    tmux new-window -t "$SESSION_NAME:1" -n "developer" -c "$PROJECT_ROOT"
    
    # Window 2: QA Bee (プロジェクトルートで起動)
    tmux new-window -t "$SESSION_NAME:2" -n "qa" -c "$PROJECT_ROOT"
    
    # Window 3: Analyst Bee (プロジェクトルートで起動)
    tmux new-window -t "$SESSION_NAME:3" -n "analyst" -c "$PROJECT_ROOT"
    
    # デフォルトでQueen Beeウィンドウを選択
    tmux select-window -t "$SESSION_NAME:0"
    
    log_success "4 windows created successfully"
}

set_window_titles() {
    log_info "Setting window titles and shortcuts..."
    
    # ウィンドウタイトルを設定（既にnew-windowで設定済み）
    # 追加でアイコン付きタイトルを設定
    tmux rename-window -t "$SESSION_NAME:0" "🐝 queen"
    tmux rename-window -t "$SESSION_NAME:1" "💻 developer" 
    tmux rename-window -t "$SESSION_NAME:2" "🔍 qa"
    tmux rename-window -t "$SESSION_NAME:3" "📊 analyst"
    
    # ステータスバーの設定を更新（ウィンドウ表示用）
    tmux set-option -t "$SESSION_NAME" status-justify centre
    tmux set-option -t "$SESSION_NAME" window-status-format " #I:#W "
    tmux set-option -t "$SESSION_NAME" window-status-current-format "#[bg=colour27,fg=colour255] #I:#W #[default]"
    
    # カスタムキーバインドの設定（移動しやすくするため）
    # デタッチと競合しないよう、別のキーを使用
    tmux bind-key -T prefix q select-window -t 0  # Queen
    tmux bind-key -T prefix w select-window -t 1  # Developer (Worker)
    tmux bind-key -T prefix e select-window -t 2  # QA (Examiner)
    tmux bind-key -T prefix r select-window -t 3  # Analyst (Researcher)
    
    # Alt + 左右矢印でウィンドウ切り替え
    tmux bind-key -T prefix Left previous-window
    tmux bind-key -T prefix Right next-window
    
    # Shift + 左右矢印でも可能に
    tmux bind-key -T prefix S-Left previous-window
    tmux bind-key -T prefix S-Right next-window
    
    log_success "Window titles and shortcuts configured successfully"
}

start_claude_instances() {
    log_info "Starting Claude CLI instances in separate windows..."
    
    # Source helper functions
    source "$PROJECT_ROOT/scripts/send_keys_helper.sh"
    
    log_info "Starting Queen Bee in window 0..."
    local queen_init="claude --dangerously-skip-permissions"
    send_keys_cli "$SESSION_NAME" "0" "$queen_init" "initialization" "queen_startup" "${BEEHIVE_DRY_RUN:-false}"
    sleep 3
    
    log_info "Starting Developer Bee in window 1..."
    local dev_init="claude --dangerously-skip-permissions"
    send_keys_cli "$SESSION_NAME" "1" "$dev_init" "initialization" "developer_startup" "${BEEHIVE_DRY_RUN:-false}"
    sleep 3
    
    log_info "Starting QA Bee in window 2..."
    local qa_init="claude --dangerously-skip-permissions"
    send_keys_cli "$SESSION_NAME" "2" "$qa_init" "initialization" "qa_startup" "${BEEHIVE_DRY_RUN:-false}"
    sleep 3
    
    log_info "Starting Analyst Bee in window 3..."
    local analyst_init="claude --dangerously-skip-permissions"
    send_keys_cli "$SESSION_NAME" "3" "$analyst_init" "initialization" "analyst_startup" "${BEEHIVE_DRY_RUN:-false}"
    sleep 3
    
    log_success "All Claude CLI instances started successfully"
}

inject_roles() {
    log_info "Injecting roles into Claude agents..."
    
    # Claude起動完了を待つ
    log_info "Waiting for Claude instances to be ready..."
    sleep 5
    
    # inject_roles.shスクリプトを実行
    if [ -f "$PROJECT_ROOT/scripts/inject_roles.sh" ]; then
        log_info "Executing role injection script..."
        if "$PROJECT_ROOT/scripts/inject_roles.sh" --all; then
            log_success "Role injection completed successfully"
            return 0
        else
            log_error "Role injection failed"
            return 1
        fi
    else
        log_error "Role injection script not found: $PROJECT_ROOT/scripts/inject_roles.sh"
        return 1
    fi
}

verify_startup() {
    log_info "Verifying startup status..."
    
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_error "tmux session does not exist"
        return 1
    fi
    
    local window_count
    window_count=$(tmux list-windows -t "$SESSION_NAME" | wc -l)
    if [ "$window_count" -ne 4 ]; then
        log_error "Invalid window count (expected: 4, actual: $window_count)"
        return 1
    fi
    
    log_success "Beehive startup verification complete"
    log_info "Next steps:"
    log_info "  1. Run ./beehive.sh attach to connect to session"
    log_info "  2. Switch between bee windows using:"
    log_info "     • Ctrl-b + q/w/e/r (Queen/Worker/Examiner/Researcher)"
    log_info "     • Ctrl-b + ←/→ (Previous/Next window)"
    log_info "     • Ctrl-b + 0/1/2/3 (Direct window selection)"
    log_info "     • Ctrl-b + d (Detach from session)"
    log_info "  3. Check each window to verify role understanding"
    log_info "  4. Use './beehive.sh start-task \"task\"' to begin work"
    
    return 0
}

main() {
    log_info "=== Beehive Initialization Started ==="
    
    check_prerequisites
    cleanup_existing_session
    create_tmux_session
    create_windows
    set_window_titles
    start_claude_instances
    
    # Claude起動後に役割注入を自動実行
    if inject_roles; then
        log_info "Role injection successful"
    else
        log_warning "Role injection failed, but continuing with initialization"
    fi
    
    if verify_startup; then
        log_success "=== Beehive Initialization Complete ==="
        log_info "Connect with: tmux attach-session -t $SESSION_NAME"
        log_info "All bees are ready for tasks!"
    else
        log_error "=== Initialization failed ==="
        exit 1
    fi
}

trap 'log_error "Unexpected error occurred (line: $LINENO)"' ERR
main "$@"