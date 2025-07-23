#!/usr/bin/env python3
"""
Tasks API endpoints for Beehive Web Dashboard
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..models.schemas import TaskListResponse, TaskCreateRequest, TaskResponse
from ..database.connection import get_db_manager

router = APIRouter()


@router.get("/", response_model=TaskListResponse)
async def get_all_tasks(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None)
):
    """Get all tasks with pagination and optional filtering"""
    try:
        db_manager = get_db_manager()
        offset = (page - 1) * per_page
        
        # Apply filters
        status_filter = status if status in ['pending', 'in_progress', 'completed', 'failed', 'cancelled'] else None
        
        tasks, total_count = db_manager.get_tasks(
            limit=per_page,
            offset=offset,
            status_filter=status_filter
        )
        
        # Additional filtering by assigned_to if specified
        if assigned_to:
            tasks = [task for task in tasks if task.assigned_to == assigned_to]
            total_count = len(tasks)
        
        return TaskListResponse(
            tasks=tasks,
            total_count=total_count,
            page=page,
            per_page=per_page,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a specific task by ID"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    task_id, title, description, status, priority,
                    assigned_to, created_at, updated_at, completed_at,
                    estimated_hours, actual_hours, created_by, metadata
                FROM tasks 
                WHERE task_id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
            
            import json
            from ..models.schemas import TaskStatus, Priority
            
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            
            return TaskResponse(
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
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.post("/", response_model=dict)
async def create_task(task_request: TaskCreateRequest):
    """Create a new task"""
    try:
        db_manager = get_db_manager()
        
        task_data = {
            'title': task_request.title,
            'description': task_request.description,
            'priority': task_request.priority.value,
            'assigned_to': task_request.assigned_to.value if task_request.assigned_to else None,
            'estimated_hours': task_request.estimated_hours,
            'created_by': 'web_dashboard',
            'metadata': {
                'created_via': 'web_dashboard',
                'web_created': True
            }
        }
        
        task_id = db_manager.create_task(task_data)
        
        return {
            "message": "Task created successfully",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.put("/{task_id}/status")
async def update_task_status(task_id: str, status: str):
    """Update task status"""
    try:
        if status not in ['pending', 'in_progress', 'completed', 'failed', 'cancelled']:
            raise HTTPException(status_code=400, detail="Invalid status value")
        
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            # Update task status
            cursor = conn.execute("""
                UPDATE tasks 
                SET status = ?, 
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled') 
                                       THEN CURRENT_TIMESTAMP 
                                       ELSE completed_at END
                WHERE task_id = ?
            """, (status, status, task_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
            
            conn.commit()
            
            return {
                "message": f"Task status updated to '{status}'",
                "task_id": task_id,
                "new_status": status,
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")


@router.put("/{task_id}/assign")
async def assign_task(task_id: str, agent_name: str):
    """Assign task to an agent"""
    try:
        if agent_name not in ['queen', 'developer', 'qa', 'analyst']:
            raise HTTPException(status_code=400, detail="Invalid agent name")
        
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tasks 
                SET assigned_to = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (agent_name, task_id))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
            
            conn.commit()
            
            return {
                "message": f"Task assigned to '{agent_name}'",
                "task_id": task_id,
                "assigned_to": agent_name,
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign task: {str(e)}")


@router.get("/{task_id}/messages")
async def get_task_messages(task_id: str):
    """Get messages related to a specific task"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    message_id, from_bee, to_bee, message_type, subject, content,
                    priority, processed, created_at, sender_cli_used
                FROM bee_messages 
                WHERE task_id = ?
                ORDER BY created_at ASC
            """, (task_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "message_id": row['message_id'],
                    "from_bee": row['from_bee'],
                    "to_bee": row['to_bee'],
                    "message_type": row['message_type'],
                    "subject": row['subject'],
                    "content": row['content'],
                    "priority": row['priority'],
                    "processed": bool(row['processed']),
                    "created_at": row['created_at'],
                    "sender_cli_used": bool(row['sender_cli_used'])
                })
            
            return {
                "task_id": task_id,
                "messages": messages,
                "message_count": len(messages),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task messages: {str(e)}")


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task (mark as cancelled)"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tasks 
                SET status = 'cancelled', 
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (task_id,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
            
            conn.commit()
            
            return {
                "message": f"Task '{task_id}' cancelled successfully",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")