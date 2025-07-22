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
    
    local tmux_version=$(tmux -V | cut -d' ' -f2)
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

create_panes() {
    log_info "Creating Bee panes..."
    
    tmux rename-window -t "$SESSION_NAME:0" "hive"
    tmux split-window -t "$SESSION_NAME:0" -v -c "$PROJECT_ROOT/workspaces/developer"
    tmux split-window -t "$SESSION_NAME:0" -h -c "$PROJECT_ROOT/workspaces/qa"
    tmux select-layout -t "$SESSION_NAME:0" main-horizontal
    
    log_success "3 panes created successfully"
}

set_pane_titles() {
    log_info "Setting pane titles..."
    
    tmux set-option -t "$SESSION_NAME" pane-border-status top
    tmux set-option -t "$SESSION_NAME" pane-border-format "#{?pane_active,#[bg=colour27]#[fg=colour255],#[bg=colour236]#[fg=colour255]} #{pane_title} #{?pane_active,#[default],#[default]}"
    
    tmux select-pane -t "$SESSION_NAME:0.0" -T "[QUEEN] Planning & Coordination"
    tmux select-pane -t "$SESSION_NAME:0.1" -T "[DEVELOPER] Implementation"
    tmux select-pane -t "$SESSION_NAME:0.2" -T "[QA] Testing & Quality"
    
    log_success "Pane titles configured successfully"
}

start_claude_instances() {
    log_info "Starting Claude CLI instances..."
    
    log_info "Starting Queen Bee (pane 0)..."
    tmux send-keys -t "$SESSION_NAME:0.0" "cd $PROJECT_ROOT/workspaces/queen" Enter
    tmux send-keys -t "$SESSION_NAME:0.0" "claude --dangerously-skip-permissions" Enter
    sleep 3
    
    log_info "Starting Developer Bee (pane 1)..."
    tmux send-keys -t "$SESSION_NAME:0.1" "cd $PROJECT_ROOT/workspaces/developer" Enter  
    tmux send-keys -t "$SESSION_NAME:0.1" "claude --dangerously-skip-permissions" Enter
    sleep 3
    
    log_info "Starting QA Bee (pane 2)..."
    tmux send-keys -t "$SESSION_NAME:0.2" "cd $PROJECT_ROOT/workspaces/qa" Enter
    tmux send-keys -t "$SESSION_NAME:0.2" "claude --dangerously-skip-permissions" Enter
    sleep 3
    
    log_success "All Claude CLI instances started successfully"
}

verify_startup() {
    log_info "Verifying startup status..."
    
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_error "tmux session does not exist"
        return 1
    fi
    
    local pane_count=$(tmux list-panes -t "$SESSION_NAME:0" | wc -l)
    if [ "$pane_count" -ne 3 ]; then
        log_error "Invalid pane count (expected: 3, actual: $pane_count)"
        return 1
    fi
    
    log_success "Beehive startup verification complete"
    log_info "Next steps:"
    log_info "  1. Run ./beehive.sh attach to connect to session"
    log_info "  2. Verify Claude is running in each pane"
    log_info "  3. Run ./scripts/inject_roles.sh to inject roles (not implemented)"
    
    return 0
}

main() {
    log_info "=== Beehive Initialization Started ==="
    
    check_prerequisites
    cleanup_existing_session
    create_tmux_session
    create_panes
    set_pane_titles
    start_claude_instances
    
    if verify_startup; then
        log_success "=== Beehive Initialization Complete ==="
        log_info "Connect with: tmux attach-session -t $SESSION_NAME"
    else
        log_error "=== Initialization failed ==="
        exit 1
    fi
}

trap 'log_error "Unexpected error occurred (line: $LINENO)"' ERR
main "$@"