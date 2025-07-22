# Makefile for Claude Multi-Agent Development System (Beehive) - PoC Version

.PHONY: help install format check quality test clean init status logs start-task pre-commit setup dev-setup

# Default target
help: ## Show available commands
	@echo "🐝 Beehive PoC Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install system dependencies and setup environment
	@echo "📦 Setting up Beehive environment..."
	@command -v tmux >/dev/null 2>&1 || (echo "❌ tmux required" && exit 1)
	@command -v claude >/dev/null 2>&1 || (echo "❌ claude CLI required" && exit 1)
	@command -v uv >/dev/null 2>&1 || (echo "❌ uv required - install: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@echo "📦 Installing Python dependencies..."
	@uv sync --extra dev --extra quality
	@echo "✅ Environment ready"

# Code Quality
format: ## Format code with ruff
	@echo "🎨 Formatting code..."
	@uv run ruff format bees/
	@uv run ruff check --fix bees/
	@echo "✅ Code formatted"

check: ## Run quality checks
	@echo "🔍 Running quality checks..."
	@uv run ruff check bees/
	@uv run ruff format --check bees/
	@echo "✅ Quality checks passed"

quality: format check ## Run comprehensive quality pipeline (format + check)
	@echo "🏆 Quality pipeline completed successfully!"

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	@uv run pytest -v
	@echo "✅ Tests completed"

# Cleanup
clean: ## Clean temporary files and sessions
	@echo "🧹 Cleaning up..."
	@rm -f *.tmp logs/*.log 2>/dev/null || true
	@tmux has-session -t beehive 2>/dev/null && echo "⚠️  Beehive session active - use 'make terminate'" || true
	@echo "✅ Cleanup completed"

# Beehive Operations
init: ## Initialize Beehive system
	@./beehive.sh init

status: ## Check Beehive status
	@./beehive.sh status

logs: ## Show Beehive logs  
	@./beehive.sh logs

terminate: ## Stop Beehive system
	@echo "y" | ./beehive.sh stop

start-task: ## Start a task (usage: make start-task TASK="description")
	@if [ -z "$(TASK)" ]; then \
		echo "❌ Usage: make start-task TASK=\"task description\""; \
		echo "📝 Example: make start-task TASK=\"Create a TODO app\""; \
		exit 1; \
	fi
	@./beehive.sh start-task "$(TASK)"

# Development Tools
pre-commit: ## Install and setup pre-commit hooks
	@./scripts/install-pre-commit.sh

# Combined Operations
setup: install init ## Full setup: install dependencies and initialize system
	@echo "🐝 Beehive PoC ready!"
	@echo "💡 Use: make start-task TASK=\"your task here\""

dev-setup: setup pre-commit ## Full development setup with pre-commit hooks
	@echo "🚀 Development environment fully configured!"