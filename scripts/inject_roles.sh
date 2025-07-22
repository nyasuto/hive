#!/bin/bash

# inject_roles.sh - Inject role definitions into Claude agents via tmux send-keys
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_NAME="beehive"

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

# Inject role into specific pane
inject_role_to_pane() {
    local pane_id="$1"
    local role_file="$2"
    local role_name="$3"
    
    log_info "Injecting $role_name role into pane $pane_id..."
    
    # Check if role file exists
    if ! check_role_file "$role_file"; then
        return 1
    fi
    
    # Send clear command first
    tmux send-keys -t "$SESSION_NAME:0.$pane_id" "clear" Enter
    sleep 1
    
    # Send role content
    log_info "Sending role definition to $role_name..."
    
    # Create temporary file for role content
    local temp_file
    temp_file=$(mktemp)
    trap 'rm -f "${temp_file:-}"' RETURN
    
    # Copy role content to temp file and add prompt
    cp "$role_file" "$temp_file"
    echo "" >> "$temp_file"
    echo "あなたの役割を理解できましたか？準備完了の場合は「準備完了」と応答してください。" >> "$temp_file"
    
    # Send content using tmux load-buffer and paste-buffer
    tmux load-buffer -t "$SESSION_NAME" "$temp_file"
    tmux paste-buffer -t "$SESSION_NAME:0.$pane_id"
    tmux send-keys -t "$SESSION_NAME:0.$pane_id" Enter
    
    log_success "$role_name role injected successfully"
    return 0
}

# Inject all roles
inject_all_roles() {
    log_info "=== Role Injection Started ==="
    
    local success_count=0
    local total_roles=3
    
    # Inject Queen Bee role (pane 0)
    if inject_role_to_pane "0" "$PROJECT_ROOT/roles/queen.md" "Queen Bee"; then
        ((success_count++))
    fi
    
    sleep 2
    
    # Inject Developer Bee role (pane 1) 
    if inject_role_to_pane "1" "$PROJECT_ROOT/roles/developer.md" "Developer Bee"; then
        ((success_count++))
    fi
    
    sleep 2
    
    # Inject QA Bee role (pane 2)
    if inject_role_to_pane "2" "$PROJECT_ROOT/roles/qa.md" "QA Bee"; then
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
        *)
            log_error "Unknown role: $role_name"
            log_info "Available roles: queen, developer, qa"
            return 1
            ;;
    esac
}

# Verify role injection
verify_roles() {
    log_info "Verifying role injection..."
    
    # Check if panes are responsive
    local responsive_panes=0
    
    for pane_id in 0 1 2; do
        # Send a simple test command
        tmux send-keys -t "$SESSION_NAME:0.$pane_id" "" Enter
        tmux send-keys -t "$SESSION_NAME:0.$pane_id" "現在の時刻を教えてください" Enter
        
        # Check if pane exists and is active
        if tmux list-panes -t "$SESSION_NAME:0" -f "#{pane_id}" | grep -q "^$pane_id"; then
            ((responsive_panes++))
        fi
    done
    
    log_info "Active panes: $responsive_panes/3"
    
    if [[ $responsive_panes -eq 3 ]]; then
        log_success "All panes are responsive"
        return 0
    else
        log_warning "Some panes may not be responsive"
        return 1
    fi
}

# Show help
show_help() {
    cat << 'EOF'
🐝 Role Injection Script for Claude Multi-Agent System

USAGE:
    ./scripts/inject_roles.sh [OPTIONS] [ROLE]

OPTIONS:
    --all, -a           Inject all roles (default)
    --verify, -v        Verify role injection
    --help, -h          Show this help

ROLES:
    queen, 0           Inject Queen Bee role (pane 0)
    developer, dev, 1  Inject Developer Bee role (pane 1)  
    qa, 2              Inject QA Bee role (pane 2)

EXAMPLES:
    ./scripts/inject_roles.sh                    # Inject all roles
    ./scripts/inject_roles.sh --all              # Inject all roles
    ./scripts/inject_roles.sh queen              # Inject Queen role only
    ./scripts/inject_roles.sh developer          # Inject Developer role only
    ./scripts/inject_roles.sh --verify           # Verify injection

REQUIREMENTS:
    - Beehive session must be running (./beehive.sh init)
    - Role definition files must exist in roles/ directory
    - Claude agents must be responsive in each pane

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
        "queen"|"developer"|"dev"|"qa"|"0"|"1"|"2")
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