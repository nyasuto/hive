# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Claude Multi-Agent Development System (Beehive)** - a tmux-based multi-agent system where AI agents collaborate on development tasks. The system uses a beehive metaphor with Queen Bee for coordination and Worker Bees for specialized tasks (Developer, QA).

## Key Technologies and Dependencies

- **Python 3.12+** with `uv` and `ruff` for code management
- **tmux (>= 3.0)** for session management and agent isolation
- **SQLite3** for inter-agent communication and state persistence
- **Claude CLI** with dangerous permissions enabled (`claude --dangerously-skip-permissions`)
- **Bash scripting** for orchestration

## Architecture Overview

**Multi-Agent Communication Flow:**
- Each agent runs in a separate tmux pane as a Claude CLI instance
- Agents communicate via SQLite database + tmux send-keys
- Queen Bee coordinates tasks, Worker Bees execute specialized roles
- Context management system prevents agent "forgetting" their roles

**Core Components:**
- `beehive.sh` - Main orchestrator and CLI interface
- `scripts/` - Setup and management automation
- `bees/` - Python classes for agent communication protocols  
- `roles/` - Markdown files defining agent behaviors and prompts
- `memory/` - Context preservation and reminder system
- `hive/` - SQLite database for shared state and communication
- `workspaces/` - Isolated working directories for each agent

## Development Commands

### Main Orchestration Commands
```bash
# Initialize the hive (start all agents in waiting state)
./beehive.sh init

# Submit task to Queen Bee (starts autonomous execution)
./beehive.sh start-task "task description"

# Check status of all agents
./beehive.sh status

# View logs for specific agent
./beehive.sh logs [queen|developer|qa]

# Attach to tmux session for direct observation
./beehive.sh attach

# Manual context reminder (anti-forgetting)
./beehive.sh remind [--bee specific_bee]

# Stop the entire hive
./beehive.sh stop
```

### Setup and Management
```bash
# Initial project setup
./scripts/setup.sh

# Manually inject roles into waiting agents  
./scripts/inject_roles.sh

# Start context reminder daemon
./scripts/reminder_daemon.sh

# Monitor system health
./scripts/monitor.sh
```

### Development Tools (when implemented)
```bash
# Quality checks using modern Python toolchain
uv run ruff check .          # Linting
uv run ruff format .         # Code formatting
python -m pytest            # Testing (when tests exist)
```

## Database Schema and Communication

**Key Tables:**
- `tasks` - Task queue and assignments between agents
- `bee_messages` - Inter-agent communication protocol  
- `bee_states` - Agent status and heartbeat tracking
- `context_snapshots` - Anti-forgetting context preservation
- `decision_log` - Important decisions and rationale tracking

**Communication Protocol:**
1. Queen assigns tasks via SQLite INSERT
2. Notification sent via `tmux send-keys`
3. Worker bees poll database and respond with status updates
4. Context manager sends periodic reminders to prevent role drift

## Anti-Forgetting System Design

**Critical Feature:** Agents periodically receive role reminders because Claude instances can forget their assigned roles during long conversations.

**Implementation:**
- Periodic context injection every 5 minutes
- Visual role reinforcement in tmux pane titles
- Decision checkpointing to SQLite
- Task transition summaries

## Agent Role Definitions

**Queen Bee (`roles/queen.md`):**
- Task decomposition and planning
- Worker coordination and progress monitoring  
- Decision making and conflict resolution

**Developer Bee (`roles/developer.md`):**
- Code implementation based on Queen's assignments
- Progress reporting to Queen via SQLite
- Collaboration with QA for testing feedback

**QA Bee (`roles/qa.md`):**
- Testing implementation from Developer
- Quality assurance and bug reporting
- Integration with CI/CD when available

## Implementation Status

**Current Phase:** Planning and design complete (comprehensive README.md exists)
**Next Steps:** Implementation should follow this order:
1. `scripts/init_hive.sh` - tmux session and Claude startup
2. `hive/schema.sql` - Database schema implementation
3. `roles/queen.md` - Queen agent role definition
4. `scripts/inject_roles.sh` - Role injection mechanism
5. `memory/context_manager.py` - Anti-forgetting system

## Troubleshooting Commands

```bash
# Verify Claude CLI setup
which claude && claude --version
claude --dangerously-skip-permissions --help

# Check tmux sessions
tmux list-sessions
tmux capture-pane -t beehive:0 -p

# Database debugging
sqlite3 hive/hive_memory.db "SELECT * FROM bee_states"
sqlite3 hive/hive_memory.db "SELECT * FROM bee_messages WHERE processed=0"

# Manual role re-injection if agents forget
./scripts/inject_roles.sh
./beehive.sh remind
```

## Security and Permissions

**IMPORTANT:** This system requires `claude --dangerously-skip-permissions` to function. This is necessary for:
- File system access across agent workspaces
- SQLite database read/write operations  
- tmux session management and inter-pane communication

Only use this system in isolated development environments.

## Language and Documentation

- Primary language: **Japanese (日本語)** - all user-facing documentation and prompts
- Code comments and technical implementation: English acceptable
- Agent role definitions and prompts: Japanese preferred for consistency with README

## Project Philosophy

This system implements **autonomous multi-agent collaboration** where human input is minimal after initial task submission. The Queen Bee acts as project manager, coordinating specialized Worker Bees without constant human oversight. The anti-forgetting system is critical for maintaining agent coherence during long-running tasks.