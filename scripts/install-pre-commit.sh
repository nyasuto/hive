#!/bin/bash
# Pre-commit hooks installation script for Beehive PoC

set -e

echo "🔧 Installing pre-commit hooks for Beehive..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    if command -v uv &> /dev/null; then
        uv sync --extra quality
    elif command -v pip &> /dev/null; then
        pip install pre-commit
    else
        echo "❌ Neither uv nor pip found. Please install pre-commit manually."
        exit 1
    fi
fi

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Run pre-commit on all files to test setup
echo "🧪 Testing pre-commit setup..."
if pre-commit run --all-files; then
    echo "✅ Pre-commit hooks installed and tested successfully!"
    echo ""
    echo "📋 Pre-commit hooks now active for:"
    echo "  - Code formatting (Ruff)"
    echo "  - Code linting (Ruff)"  
    echo "  - Security scanning (Bandit)"
    echo "  - Type checking (mypy)"
    echo "  - Shell script linting (shellcheck)"
    echo "  - File quality checks"
    echo ""
    echo "💡 To manually run checks: pre-commit run --all-files"
else
    echo "⚠️  Pre-commit setup completed with some issues."
    echo "   Run 'make format' to fix any formatting issues."
    echo "   Then run 'pre-commit run --all-files' to verify."
fi

echo ""
echo "🎉 Pre-commit setup complete!"