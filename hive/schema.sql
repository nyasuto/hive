-- Claude Multi-Agent System (Beehive) Database Schema
-- Task Execution and Communication System for Issue #3
-- SQLite Database Schema for Multi-Agent Collaboration

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ====================
-- TASK MANAGEMENT TABLES
-- ====================

-- Main tasks table - stores all tasks assigned to the hive
CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY, -- UUID-based task identifier
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'cancelled')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    assigned_to TEXT, -- 'queen', 'developer', 'qa', 'analyst', or NULL for unassigned
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    due_date DATETIME,
    estimated_hours REAL,
    actual_hours REAL,
    tags TEXT, -- JSON array of tags
    metadata TEXT, -- JSON for additional task data
    parent_task_id TEXT REFERENCES tasks(task_id),
    created_by TEXT DEFAULT 'human' -- 'human', 'queen', 'developer', 'qa', 'analyst'
);

-- Task dependencies - manage task ordering and dependencies
CREATE TABLE IF NOT EXISTS task_dependencies (
    dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    depends_on_task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL DEFAULT 'blocks' CHECK (dependency_type IN ('blocks', 'related', 'subtask')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, depends_on_task_id)
);

-- Task assignments and work distribution
CREATE TABLE IF NOT EXISTS task_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    assigned_to TEXT NOT NULL, -- 'queen', 'developer', 'qa', 'analyst'
    assigned_by TEXT NOT NULL, -- who made the assignment
    assignment_type TEXT NOT NULL DEFAULT 'primary' CHECK (assignment_type IN ('primary', 'reviewer', 'collaborator')),
    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    completed_at DATETIME,
    status TEXT NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned', 'accepted', 'in_progress', 'completed', 'declined')),
    notes TEXT
);

-- Task activity log - track all changes and activities
CREATE TABLE IF NOT EXISTS task_activity (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    bee_name TEXT NOT NULL, -- 'queen', 'developer', 'qa', 'analyst', 'system'
    activity_type TEXT NOT NULL, -- 'created', 'updated', 'assigned', 'started', 'completed', 'comment', etc.
    description TEXT NOT NULL,
    old_value TEXT, -- for tracking changes
    new_value TEXT, -- for tracking changes
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON for additional activity data
);

-- ====================
-- BEE COMMUNICATION TABLES
-- ====================

-- Inter-bee messaging system
CREATE TABLE IF NOT EXISTS bee_messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_bee TEXT NOT NULL, -- 'queen', 'developer', 'qa', 'analyst', 'system'
    to_bee TEXT NOT NULL, -- 'queen', 'developer', 'qa', 'analyst', 'all'
    message_type TEXT NOT NULL DEFAULT 'info' CHECK (message_type IN ('info', 'question', 'request', 'response', 'alert', 'task_update')),
    subject TEXT,
    content TEXT NOT NULL,
    task_id TEXT REFERENCES tasks(task_id), -- optional task reference
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    reply_to INTEGER REFERENCES bee_messages(message_id),
    metadata TEXT -- JSON for additional message data
);

-- Bee state tracking - monitor agent status and health
CREATE TABLE IF NOT EXISTS bee_states (
    state_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bee_name TEXT NOT NULL UNIQUE, -- 'queen', 'developer', 'qa', 'analyst'
    status TEXT NOT NULL DEFAULT 'idle' CHECK (status IN ('idle', 'busy', 'waiting', 'offline', 'error')),
    current_task_id TEXT REFERENCES tasks(task_id),
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
    capabilities TEXT, -- JSON array of bee capabilities
    workload_score REAL DEFAULT 0, -- 0-100 score indicating current workload
    performance_score REAL DEFAULT 100, -- 0-100 performance rating
    metadata TEXT, -- JSON for additional state data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Context and memory management for forgetting countermeasures
CREATE TABLE IF NOT EXISTS context_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bee_name TEXT NOT NULL,
    context_type TEXT NOT NULL CHECK (context_type IN ('role', 'task', 'conversation', 'system')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    task_id TEXT REFERENCES tasks(task_id),
    importance_score INTEGER DEFAULT 5 CHECK (importance_score BETWEEN 1 AND 10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    metadata TEXT -- JSON for additional context data
);

-- ====================
-- COLLABORATION TABLES
-- ====================

-- Work handoffs between bees
CREATE TABLE IF NOT EXISTS work_handoffs (
    handoff_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    from_bee TEXT NOT NULL,
    to_bee TEXT NOT NULL,
    handoff_type TEXT NOT NULL CHECK (handoff_type IN ('assignment', 'review', 'collaboration', 'escalation')),
    description TEXT NOT NULL,
    deliverables TEXT, -- JSON array of deliverables
    requirements TEXT, -- JSON array of requirements
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'in_progress', 'completed', 'rejected')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    completed_at DATETIME,
    notes TEXT
);

-- Quality gates and checkpoints
CREATE TABLE IF NOT EXISTS quality_gates (
    gate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    gate_name TEXT NOT NULL,
    gate_type TEXT NOT NULL CHECK (gate_type IN ('code_review', 'testing', 'documentation', 'approval', 'deployment')),
    criteria TEXT NOT NULL, -- JSON array of gate criteria
    assigned_to TEXT NOT NULL, -- usually 'qa' but can be others
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'passed', 'failed', 'skipped')),
    result TEXT, -- JSON with detailed results
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    notes TEXT
);

-- ====================
-- INDEXES FOR PERFORMANCE
-- ====================

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);

CREATE INDEX IF NOT EXISTS idx_bee_messages_to_bee ON bee_messages(to_bee);
CREATE INDEX IF NOT EXISTS idx_bee_messages_processed ON bee_messages(processed);
CREATE INDEX IF NOT EXISTS idx_bee_messages_task_id ON bee_messages(task_id);
CREATE INDEX IF NOT EXISTS idx_bee_messages_created_at ON bee_messages(created_at);

CREATE INDEX IF NOT EXISTS idx_task_activity_task_id ON task_activity(task_id);
CREATE INDEX IF NOT EXISTS idx_task_activity_created_at ON task_activity(created_at);

CREATE INDEX IF NOT EXISTS idx_context_snapshots_bee_name ON context_snapshots(bee_name);
CREATE INDEX IF NOT EXISTS idx_context_snapshots_task_id ON context_snapshots(task_id);
CREATE INDEX IF NOT EXISTS idx_context_snapshots_created_at ON context_snapshots(created_at);

-- ====================
-- TRIGGERS FOR AUTOMATION
-- ====================

-- Auto-update updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_tasks_timestamp
    AFTER UPDATE ON tasks
    FOR EACH ROW
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
END;

CREATE TRIGGER IF NOT EXISTS update_bee_states_timestamp
    AFTER UPDATE ON bee_states
    FOR EACH ROW
BEGIN
    UPDATE bee_states SET updated_at = CURRENT_TIMESTAMP WHERE bee_name = NEW.bee_name;
END;

-- Auto-create task activity entries for important changes
CREATE TRIGGER IF NOT EXISTS log_task_status_changes
    AFTER UPDATE OF status ON tasks
    FOR EACH ROW
    WHEN OLD.status != NEW.status
BEGIN
    INSERT INTO task_activity (task_id, bee_name, activity_type, description, old_value, new_value)
    VALUES (NEW.task_id, 'system', 'status_change', 'Task status changed', OLD.status, NEW.status);
END;

CREATE TRIGGER IF NOT EXISTS log_task_assignment_changes
    AFTER UPDATE OF assigned_to ON tasks
    FOR EACH ROW
    WHEN OLD.assigned_to != NEW.assigned_to OR (OLD.assigned_to IS NULL AND NEW.assigned_to IS NOT NULL)
BEGIN
    INSERT INTO task_activity (task_id, bee_name, activity_type, description, old_value, new_value)
    VALUES (NEW.task_id, 'system', 'assignment_change', 'Task assignment changed', OLD.assigned_to, NEW.assigned_to);
END;

-- ====================
-- INITIAL DATA SETUP
-- ====================

-- Initialize bee states for the four standard bees including analyst
INSERT OR IGNORE INTO bee_states (bee_name, status, capabilities) VALUES
('queen', 'idle', '["task_management", "coordination", "planning", "delegation"]'),
('developer', 'idle', '["coding", "implementation", "debugging", "refactoring"]'),
('qa', 'idle', '["testing", "quality_assurance", "bug_reporting", "validation"]'),
('analyst', 'idle', '["performance_analysis", "code_metrics", "quality_assessment", "report_generation", "trend_analysis"]');

-- ====================
-- VIEWS FOR COMMON QUERIES
-- ====================

-- Active tasks view
CREATE VIEW IF NOT EXISTS active_tasks AS
SELECT 
    t.*,
    bs.status as assignee_status,
    COUNT(td.depends_on_task_id) as dependency_count,
    COUNT(tc.task_id) as child_count
FROM tasks t
LEFT JOIN bee_states bs ON t.assigned_to = bs.bee_name
LEFT JOIN task_dependencies td ON t.task_id = td.task_id
LEFT JOIN tasks tc ON t.task_id = tc.parent_task_id
WHERE t.status IN ('pending', 'in_progress')
GROUP BY t.task_id;

-- Pending messages view
CREATE VIEW IF NOT EXISTS pending_messages AS
SELECT 
    bm.*,
    t.title as task_title,
    t.status as task_status
FROM bee_messages bm
LEFT JOIN tasks t ON bm.task_id = t.task_id
WHERE bm.processed = FALSE
  AND (bm.expires_at IS NULL OR bm.expires_at > CURRENT_TIMESTAMP)
ORDER BY bm.priority DESC, bm.created_at ASC;

-- Bee workload view
CREATE VIEW IF NOT EXISTS bee_workload AS
SELECT 
    bs.bee_name,
    bs.status,
    bs.workload_score,
    COUNT(t.task_id) as active_task_count,
    COUNT(ta.assignment_id) as total_assignments,
    bs.last_heartbeat
FROM bee_states bs
LEFT JOIN tasks t ON bs.bee_name = t.assigned_to AND t.status IN ('pending', 'in_progress')
LEFT JOIN task_assignments ta ON bs.bee_name = ta.assigned_to AND ta.status IN ('assigned', 'accepted', 'in_progress')
GROUP BY bs.bee_name;

-- Task progress summary
CREATE VIEW IF NOT EXISTS task_progress AS
SELECT 
    DATE(created_at) as date,
    status,
    COUNT(*) as task_count,
    AVG(actual_hours) as avg_hours
FROM tasks
GROUP BY DATE(created_at), status
ORDER BY date DESC, status;