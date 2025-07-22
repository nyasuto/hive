#!/bin/bash

# install.sh - Install git hooks for Claude Multi-Agent Development System (Beehive)

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

main() {
    echo -e "${BLUE}🐝 Installing Beehive Git Hooks${NC}"
    echo "=================================="
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        echo "❌ Error: Not in a git repository"
        exit 1
    fi
    
    # Get git directory
    local git_dir
    git_dir=$(git rev-parse --git-dir)
    local hooks_dir="$git_dir/hooks"
    
    # Create hooks directory if it doesn't exist
    mkdir -p "$hooks_dir"
    
    # Install pre-commit hook
    if [[ -f ".githooks/pre-commit" ]]; then
        cp ".githooks/pre-commit" "$hooks_dir/pre-commit"
        chmod +x "$hooks_dir/pre-commit"
        print_success "pre-commit hook installed"
    else
        print_warning "pre-commit hook not found in .githooks/"
    fi
    
    # Set git hooks path to use our custom hooks directory
    git config core.hooksPath .githooks
    print_success "Git hooks path configured"
    
    # Make all hooks executable
    chmod +x .githooks/*
    print_success "Hook permissions set"
    
    echo ""
    print_info "Git hooks installed successfully!"
    print_info ""
    print_info "The following checks will now run on every commit:"
    print_info "• Branch naming convention enforcement"
    print_info "• Prevention of direct commits to main"
    print_info "• Shell script syntax and quality checks"
    print_info "• Forbidden content detection"
    print_info "• File size validation"
    print_info "• Permission checks"
    print_info ""
    print_info "To bypass hooks (not recommended): git commit --no-verify"
    print_info "To uninstall hooks: git config --unset core.hooksPath"
}

main "$@"