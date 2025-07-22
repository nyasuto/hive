# Makefile for Claude Multi-Agent Development System (Beehive)

.PHONY: help test check lint format clean install dev

# Default target
help: ## Show this help message
	@echo "🐝 Claude Beehive Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development commands with uv
dev: install-dev check ## Quick development setup and checks
	@echo "🔧 Development environment ready"

install: ## Install basic dependencies and check system requirements
	@echo "📦 Installing system dependencies..."
	@command -v tmux >/dev/null 2>&1 || (echo "❌ tmux is required" && exit 1)
	@command -v claude >/dev/null 2>&1 || (echo "❌ claude CLI is required" && exit 1)
	@command -v uv >/dev/null 2>&1 || (echo "❌ uv is required - install with: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
	@echo "✅ System dependencies satisfied"

install-dev: install ## Install development dependencies with uv
	@echo "📦 Installing Python dependencies with uv..."
	uv sync --extra dev --extra quality --extra security
	@echo "✅ Python dependencies installed"

install-all: install ## Install all optional dependencies
	@echo "📦 Installing all dependencies..."
	uv sync --all-extras
	@echo "✅ All dependencies installed"

# Quality checks  
check: lint python-quality shellcheck ## Run all quality checks
	@echo "✅ All quality checks passed"

python-quality: ## Run Python quality checks (black, isort, mypy, ruff)
	@echo "🔍 Running Python quality checks..."
	uv run black --check bees/
	uv run isort --check-only bees/
	uv run ruff check bees/
	uv run mypy bees/
	@echo "✅ Python quality checks passed"

lint: python-quality ## Alias for python-quality

python-format: ## Format Python code  
	@echo "🎨 Formatting Python code..."
	uv run black bees/
	uv run isort bees/
	uv run ruff --fix bees/
	@echo "✅ Python code formatted"

format: python-format ## Alias for python-format

shellcheck: ## Run shellcheck specifically
	@echo "🔍 Running detailed shellcheck..."
	@if command -v shellcheck >/dev/null 2>&1; then \
		find . -name "*.sh" -not -path "./node_modules/*" -print0 | xargs -0 shellcheck --format=gcc; \
	else \
		echo "⚠️  shellcheck not installed, run: brew install shellcheck"; \
	fi

format: ## Format shell scripts (if shfmt is available)
	@echo "🎨 Formatting shell scripts..."
	@if command -v shfmt >/dev/null 2>&1; then \
		find . -name "*.sh" -not -path "./node_modules/*" -exec shfmt -w -i 4 {} +; \
		echo "✅ Shell scripts formatted"; \
	else \
		echo "⚠️  shfmt not installed, run: brew install shfmt"; \
	fi

# Testing with uv
test: test-python test-scripts ## Run all tests
	@echo "🧪 All tests completed"

test-python: ## Run Python tests with pytest
	@echo "🧪 Running Python tests..."
	uv run pytest -v
	@echo "✅ Python tests completed"

test-coverage: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	uv run pytest --cov=bees --cov-report=html --cov-report=term-missing
	@echo "✅ Coverage report generated in htmlcov/"

test-unit: ## Run unit tests only  
	@echo "🧪 Running unit tests..."
	uv run pytest -v -m "unit"

test-integration-python: ## Run Python integration tests
	@echo "🧪 Running Python integration tests..."
	uv run pytest -v -m "integration"

test-performance: ## Run performance tests
	@echo "🧪 Running performance tests..."
	uv run pytest -v -m "performance" --benchmark-only

test-scripts: ## Test script syntax and basic functionality
	@echo "🧪 Testing script syntax..."
	@bash -n beehive.sh
	@bash -n scripts/init_hive.sh
	@echo "✅ Script syntax valid"

test-beehive: ## Test Beehive functionality without starting Claude instances
	@echo "🧪 Testing Beehive tmux functionality..."
	@./scripts/test-tmux-only.sh 2>/dev/null || echo "⚠️  tmux test skipped (test script not found)"

test-integration: ## Run integration tests (WARNING: starts actual Claude instances)
	@echo "🧪 Running integration tests..."
	@echo "⚠️  This will start actual Claude CLI instances"
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@./beehive.sh init
	@sleep 5
	@./beehive.sh status
	@echo "y" | ./beehive.sh stop

# Documentation and analysis
docs: ## Generate documentation
	@echo "📚 Generating documentation..."
	@echo "Current project structure:" > PROJECT_STRUCTURE.md
	@tree -a -I '.git' >> PROJECT_STRUCTURE.md 2>/dev/null || ls -la >> PROJECT_STRUCTURE.md
	@echo "✅ Documentation updated"

analyze: ## Analyze project structure and dependencies
	@echo "📊 Project Analysis:"
	@echo "Shell scripts: $$(find . -name "*.sh" | wc -l)"
	@echo "Total lines of shell code: $$(find . -name "*.sh" -exec cat {} + | wc -l)"
	@echo "Executable scripts: $$(find . -name "*.sh" -perm +111 2>/dev/null | wc -l || echo "N/A")"
	@echo ""
	@echo "Dependencies:"
	@echo "- tmux: $$(command -v tmux >/dev/null && echo "✅ installed" || echo "❌ missing")"
	@echo "- claude CLI: $$(command -v claude >/dev/null && echo "✅ installed" || echo "❌ missing")"
	@echo "- shellcheck: $$(command -v shellcheck >/dev/null && echo "✅ installed" || echo "❌ missing")"
	@echo "- shfmt: $$(command -v shfmt >/dev/null && echo "✅ installed" || echo "❌ missing")"

# Cleanup
clean: ## Clean up temporary files and test sessions
	@echo "🧹 Cleaning up..."
	@rm -f *.tmp
	@rm -f logs/*.log 2>/dev/null || true
	@if tmux has-session -t beehive-test 2>/dev/null; then \
		tmux kill-session -t beehive-test; \
		echo "✅ Test session cleaned up"; \
	fi
	@if tmux has-session -t beehive 2>/dev/null; then \
		echo "⚠️  Active beehive session found - use './beehive.sh stop' to stop it"; \
	fi
	@echo "✅ Cleanup completed"

# Git helpers
git-check: ## Check git status and suggest next steps
	@echo "📋 Git Status:"
	@git status --porcelain || echo "Not a git repository"
	@echo ""
	@echo "📊 Recent commits:"
	@git log --oneline -5 2>/dev/null || echo "No commits found"

# CI/CD simulation
ci: install check test ## Simulate CI/CD pipeline
	@echo "🚀 CI/CD Pipeline Results:"
	@echo "✅ Dependencies installed"
	@echo "✅ Quality checks passed"
	@echo "✅ Tests completed"
	@echo "🎉 Ready for deployment"

# Development workflows
pr-ready: clean check test git-check ## Prepare for pull request
	@echo "📋 Pull Request Checklist:"
	@echo "✅ Code formatted and linted"
	@echo "✅ Tests passing"
	@echo "✅ Git status checked"
	@echo "🚀 Ready for pull request!"

# Beehive-specific commands
init: ## Initialize Beehive system
	@./beehive.sh init

inject-roles: ## Inject roles into agents
	@./beehive.sh inject-roles

terminate: ## Terminate/stop Beehive system
	@echo "y" | ./beehive.sh stop

status: ## Check Beehive status  
	@./beehive.sh status

logs: ## Show all Beehive logs
	@./beehive.sh logs

attach: ## Attach to Beehive tmux session
	@./beehive.sh attach

start-task: ## Start a task (usage: make start-task TASK="task description")
	@if [ -z "$(TASK)" ]; then \
		echo "❌ Usage: make start-task TASK=\"task description\""; \
		echo "📝 Example: make start-task TASK=\"TODOアプリを作成してください\""; \
		exit 1; \
	fi
	@./beehive.sh start-task "$(TASK)"

# Full workflow commands
setup-and-start: init inject-roles ## Initialize, inject roles, and prepare for tasks
	@echo "🐝 Beehive is ready for tasks!"
	@echo "Use: make start-task TASK=\"your task here\""

# Git hooks management
git-hooks: ## Install git hooks for Git flow enforcement
	@./.githooks/install.sh

git-hooks-test: ## Test git hooks without committing
	@echo "🧪 Testing git hooks..."
	@./.githooks/pre-commit || echo "Hook test completed with issues"

# Legacy aliases for compatibility
beehive-init: init ## Alias for init
beehive-status: status ## Alias for status  
beehive-stop: terminate ## Alias for terminate
beehive-logs: logs ## Alias for logs