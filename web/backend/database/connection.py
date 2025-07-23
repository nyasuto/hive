#!/usr/bin/env python3
"""
Database connection and operations for Beehive Web Dashboard
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from ..models.schemas import (
    AgentStatusResponse, TaskResponse, MessageResponse,
    AgentType, AgentStatus, TaskStatus, Priority
)


class DatabaseManager:
    """Database connection and query manager"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to project hive database
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / "hive" / "hive_memory.db"
        
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def get_agents_status(self) -> List[AgentStatusResponse]:
        """Get status of all agents"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    bee_name,
                    status,
                    current_task_id,
                    last_activity,
                    last_heartbeat,
                    capabilities,
                    workload_score,
                    performance_score,
                    metadata
                FROM bee_states
                ORDER BY bee_name
            """)
            
            agents = []
            for row in cursor.fetchall():
                # Get current task title if exists
                current_task_title = None
                if row['current_task_id']:
                    task_cursor = conn.execute(
                        "SELECT title FROM tasks WHERE task_id = ?",
                        (row['current_task_id'],)
                    )
                    task_row = task_cursor.fetchone()
                    if task_row:
                        current_task_title = task_row['title']
                
                # Parse JSON fields
                capabilities = json.loads(row['capabilities']) if row['capabilities'] else []
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                
                agents.append(AgentStatusResponse(
                    name=AgentType(row['bee_name']),
                    status=AgentStatus(row['status']),
                    current_task_id=row['current_task_id'],
                    current_task_title=current_task_title,
                    last_activity=datetime.fromisoformat(row['last_activity']),
                    last_heartbeat=datetime.fromisoformat(row['last_heartbeat']),
                    workload_score=row['workload_score'] or 0.0,
                    performance_score=row['performance_score'] or 100.0,
                    capabilities=capabilities,
                    metadata=metadata
                ))
            
            return agents
    
    def get_tasks(self, limit: int = 50, offset: int = 0, status_filter: Optional[str] = None) -> Tuple[List[TaskResponse], int]:
        """Get tasks with pagination and optional status filter"""
        with self.get_connection() as conn:
            # Build query with optional filter
            where_clause = ""
            params = []
            
            if status_filter:
                where_clause = "WHERE status = ?"
                params.append(status_filter)
            
            # Get total count
            count_cursor = conn.execute(f"""
                SELECT COUNT(*) FROM tasks {where_clause}
            """, params)
            total_count = count_cursor.fetchone()[0]
            
            # Get tasks with pagination
            params.extend([limit, offset])
            cursor = conn.execute(f"""
                SELECT 
                    task_id, title, description, status, priority,
                    assigned_to, created_at, updated_at, completed_at,
                    estimated_hours, actual_hours, created_by, metadata
                FROM tasks 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, params)
            
            tasks = []
            for row in cursor.fetchall():
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                
                tasks.append(TaskResponse(
                    task_id=row['task_id'],
                    title=row['title'],
                    description=row['description'],
                    status=TaskStatus(row['status']),
                    priority=Priority(row['priority']),
                    assigned_to=row['assigned_to'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    estimated_hours=row['estimated_hours'],
                    actual_hours=row['actual_hours'],
                    created_by=row['created_by'],
                    metadata=metadata
                ))
            
            return tasks, total_count
    
    def get_messages(self, limit: int = 50, offset: int = 0, conversation_id: Optional[str] = None) -> Tuple[List[MessageResponse], int]:
        """Get messages with pagination and optional conversation filter"""
        with self.get_connection() as conn:
            # Build query with optional filter
            where_clause = ""
            params = []
            
            if conversation_id:
                where_clause = "WHERE conversation_id = ?"
                params.append(conversation_id)
            
            # Get total count
            count_cursor = conn.execute(f"""
                SELECT COUNT(*) FROM bee_messages {where_clause}
            """, params)
            total_count = count_cursor.fetchone()[0]
            
            # Get messages with pagination
            params.extend([limit, offset])
            cursor = conn.execute(f"""
                SELECT 
                    message_id, from_bee, to_bee, message_type, subject, content,
                    task_id, priority, processed, processed_at, created_at,
                    sender_cli_used, conversation_id
                FROM bee_messages 
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, params)
            
            messages = []
            for row in cursor.fetchall():
                messages.append(MessageResponse(
                    message_id=row['message_id'],
                    from_bee=row['from_bee'],
                    to_bee=row['to_bee'],
                    message_type=row['message_type'],
                    subject=row['subject'],
                    content=row['content'],
                    task_id=row['task_id'],
                    priority=Priority(row['priority']),
                    processed=bool(row['processed']),
                    processed_at=datetime.fromisoformat(row['processed_at']) if row['processed_at'] else None,
                    created_at=datetime.fromisoformat(row['created_at']),
                    sender_cli_used=bool(row['sender_cli_used']),
                    conversation_id=row['conversation_id']
                ))
            
            return messages, total_count
    
    def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task"""
        import uuid
        task_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO tasks (
                    task_id, title, description, status, priority,
                    assigned_to, estimated_hours, created_by, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                task_data['title'],
                task_data['description'],
                task_data.get('status', 'pending'),
                task_data.get('priority', 'medium'),
                task_data.get('assigned_to'),
                task_data.get('estimated_hours'),
                task_data.get('created_by', 'web_dashboard'),
                json.dumps(task_data.get('metadata', {}))
            ))
            conn.commit()
        
        return task_id
    
    def insert_beekeeper_instruction(self, instruction_data: Dict[str, Any]) -> int:
        """Insert a beekeeper instruction message"""
        import uuid
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO bee_messages (
                    from_bee, to_bee, message_type, subject, content,
                    priority, sender_cli_used, conversation_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'beekeeper',
                instruction_data['target_agent'],
                'instruction',
                instruction_data.get('subject', 'Web Dashboard Instruction'),
                instruction_data['content'],
                instruction_data.get('priority', 'medium'),
                True,  # Web dashboard uses sender CLI
                str(uuid.uuid4())
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get conversation statistics"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    SUM(CASE WHEN from_bee = 'beekeeper' THEN 1 ELSE 0 END) as beekeeper_instructions,
                    SUM(CASE WHEN from_bee != 'beekeeper' THEN 1 ELSE 0 END) as bee_conversations,
                    AVG(CASE WHEN sender_cli_used THEN 1.0 ELSE 0.0 END) * 100 as cli_usage_rate,
                    COUNT(DISTINCT conversation_id) as active_conversations
                FROM bee_messages
                WHERE created_at >= datetime('now', '-24 hours')
            """)
            
            row = cursor.fetchone()
            return {
                'total_messages': row['total_messages'] or 0,
                'beekeeper_instructions': row['beekeeper_instructions'] or 0,
                'bee_conversations': row['bee_conversations'] or 0,
                'sender_cli_usage_rate': round(row['cli_usage_rate'] or 0, 2),
                'active_conversations': row['active_conversations'] or 0
            }
    
    def check_database_health(self) -> bool:
        """Check if database is accessible and healthy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
                return True
        except Exception:
            return False


# Singleton instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get singleton database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager