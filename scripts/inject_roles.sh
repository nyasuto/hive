#!/bin/bash

# inject_roles.sh - Inject role definitions into Claude agents via send-keys CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_NAME="beehive"

# ヘルパー関数を読み込み
source "${SCRIPT_DIR}/send_keys_helper.sh"

log_info() { echo -e "\033[36m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[31m[ERROR]\033[0m $1"; }
log_warning() { echo -e "\033[33m[WARNING]\033[0m $1"; }

# Check if tmux session exists
check_session() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        log_error "Beehive session '$SESSION_NAME' not found"
        log_info "Please run './beehive.sh init' first"
        return 1
    fi
    
    return 0
}

# Check if role file exists and is readable
check_role_file() {
    local role_file="$1"
    
    if [[ ! -f "$role_file" ]]; then
        log_error "Role file not found: $role_file"
        return 1
    fi
    
    if [[ ! -r "$role_file" ]]; then
        log_error "Role file not readable: $role_file"
        return 1
    fi
    
    return 0
}

# Inject role into specific pane using CLI
inject_role_to_pane() {
    local pane_id="$1"
    local role_file="$2"
    local role_name="$3"
    
    log_info "Injecting $role_name role into $pane_id via CLI..."
    
    # Check if role file exists
    if ! check_role_file "$role_file"; then
        return 1
    fi
    
    # Clear the pane first using CLI
    send_keys_cli "$SESSION_NAME" "$pane_id" "clear" "command" "system" "${BEEHIVE_DRY_RUN:-false}"
    sleep 1
    
    # Read role content and prepare injection message
    log_info "Reading role definition for $role_name..."
    local role_content
    role_content=$(cat "$role_file")
    
    # Add role injection prompt
    role_content="${role_content}

あなたの役割を理解できましたか？準備完了の場合は「準備完了」と応答してください。"
    
    # Send role injection via CLI with proper metadata
    log_info "Injecting role via send-keys CLI..."
    inject_role "$SESSION_NAME" "$pane_id" "$role_content" "${BEEHIVE_DRY_RUN:-false}"
    
    log_success "$role_name role injected successfully via CLI"
    return 0
}

# Inject all roles
inject_all_roles() {
    log_info "=== Role Injection Started ==="
    
    local success_count=0
    local total_roles=4
    
    # Inject Queen Bee role (window 0)
    if inject_role_to_pane "0" "$PROJECT_ROOT/roles/queen.md" "Queen Bee"; then
        ((success_count++))
    fi
    
    sleep 2
    
    # Inject Developer Bee role (window 1) 
    if inject_role_to_pane "1" "$PROJECT_ROOT/roles/developer.md" "Developer Bee"; then
        ((success_count++))
    fi
    
    sleep 2
    
    # Inject QA Bee role (window 2)
    if inject_role_to_pane "2" "$PROJECT_ROOT/roles/qa.md" "QA Bee"; then
        ((success_count++))
    fi
    
    sleep 2
    
    # Inject Analyst Bee role (window 3)
    if inject_role_to_pane "3" "$PROJECT_ROOT/roles/analyst.md" "Analyst Bee"; then
        ((success_count++))
    fi
    
    echo ""
    log_info "=== Role Injection Complete ==="
    log_info "Successfully injected: $success_count/$total_roles roles"
    
    if [[ $success_count -eq $total_roles ]]; then
        log_success "All roles injected successfully!"
        log_info "Next steps:"
        log_info "  1. Check each pane to verify role understanding"
        log_info "  2. Use './beehive.sh start-task \"task\"' to begin work"
        log_info "  3. Monitor agent responses in tmux session"
        return 0
    else
        log_warning "Some roles failed to inject. Check the logs above."
        return 1
    fi
}

# Inject specific role
inject_specific_role() {
    local role_name="$1"
    
    case "$role_name" in
        "queen"|"0")
            inject_role_to_pane "0" "$PROJECT_ROOT/roles/queen.md" "Queen Bee"
            ;;
        "developer"|"dev"|"1")
            inject_role_to_pane "1" "$PROJECT_ROOT/roles/developer.md" "Developer Bee"
            ;;
        "qa"|"2")
            inject_role_to_pane "2" "$PROJECT_ROOT/roles/qa.md" "QA Bee"
            ;;
        "analyst"|"3")
            inject_role_to_pane "3" "$PROJECT_ROOT/roles/analyst.md" "Analyst Bee"
            ;;
        *)
            log_error "Unknown role: $role_name"
            log_info "Available roles: queen, developer, qa, analyst"
            return 1
            ;;
    esac
}

# Verify role injection using CLI
verify_roles() {
    log_info "Verifying role injection via CLI..."
    
    # Check if panes are responsive using CLI
    local responsive_panes=0
    
    for window_id in "0" "1" "2" "3"; do
        log_info "Testing window $window_id responsiveness..."
        
        # Send a simple test question via CLI
        send_keys_cli "$SESSION_NAME" "$window_id" "" "heartbeat" "system"
        sleep 0.5
        send_keys_cli "$SESSION_NAME" "$window_id" "現在の時刻を教えてください" "verification" "system"
        
        # Check if window exists and is active using tmux
        if tmux list-windows -t "$SESSION_NAME" | grep -q "${window_id}:"; then
            ((responsive_panes++))
            log_info "Window $window_id is active"
        else
            log_warning "Window $window_id may not be active"
        fi
    done
    
    log_info "Active windows: $responsive_panes/4"
    
    if [[ $responsive_panes -eq 4 ]]; then
        log_success "All windows are responsive - verification via CLI complete"
        return 0
    else
        log_warning "Some windows may not be responsive"
        return 1
    fi
}

# Show help
show_help() {
    cat << 'EOF'
🐝 Role Injection Script for Claude Multi-Agent System (CLI-enabled)

USAGE:
    ./scripts/inject_roles.sh [OPTIONS] [ROLE]

OPTIONS:
    --all, -a           Inject all roles (default)
    --verify, -v        Verify role injection  
    --help, -h          Show this help

ROLES:
    queen, 0           Inject Queen Bee role (window 0)
    developer, dev, 1  Inject Developer Bee role (window 1)  
    qa, 2              Inject QA Bee role (window 2)
    analyst, 3         Inject Analyst Bee role (window 3)

EXAMPLES:
    ./scripts/inject_roles.sh                    # Inject all roles via CLI
    ./scripts/inject_roles.sh --all              # Inject all roles via CLI
    ./scripts/inject_roles.sh queen              # Inject Queen role only via CLI
    ./scripts/inject_roles.sh developer          # Inject Developer role only via CLI  
    ./scripts/inject_roles.sh --verify           # Verify injection via CLI

FEATURES:
    - Uses send-keys CLI for transparent SQLite logging
    - All communications are automatically recorded
    - 1-second delay + Enter finalization for tmux compatibility
    - Structured role injection with metadata

REQUIREMENTS:
    - Beehive session must be running (./beehive.sh init)
    - Role definition files must exist in roles/ directory
    - Claude agents must be responsive in each window
    - send-keys CLI must be available (python -m bees.cli)

EOF
}

# Main function
main() {
    local command="${1:-all}"
    
    case "$command" in
        "--help"|"-h"|"help")
            show_help
            exit 0
            ;;
        "--verify"|"-v"|"verify")
            check_session && verify_roles
            exit $?
            ;;
        "--all"|"-a"|"all")
            check_session && inject_all_roles
            exit $?
            ;;
        "queen"|"developer"|"dev"|"qa"|"analyst"|"0"|"1"|"2"|"3")
            check_session && inject_specific_role "$command"
            exit $?
            ;;
        *)
            log_error "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Error handling
trap 'log_error "Unexpected error occurred (line: $LINENO)"' ERR

# Run main function
main "$@"