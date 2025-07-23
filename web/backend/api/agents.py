#!/usr/bin/env python3
"""
Agents API endpoints for Beehive Web Dashboard
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List

from models.schemas import AgentListResponse, AgentStatusResponse
from database.connection import get_db_manager

router = APIRouter()


@router.get("/", response_model=AgentListResponse)
async def get_all_agents():
    """Get status of all agents in the hive"""
    try:
        db_manager = get_db_manager()
        agents = db_manager.get_agents_status()
        
        active_count = len([agent for agent in agents if agent.status.value != 'offline'])
        
        return AgentListResponse(
            agents=agents,
            total_count=len(agents),
            active_count=active_count,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agents status: {str(e)}")


@router.get("/{agent_name}", response_model=AgentStatusResponse)
async def get_agent_status(agent_name: str):
    """Get status of a specific agent"""
    try:
        db_manager = get_db_manager()
        agents = db_manager.get_agents_status()
        
        # Find the specific agent
        for agent in agents:
            if agent.name.value == agent_name:
                return agent
        
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


@router.get("/{agent_name}/tasks")
async def get_agent_tasks(agent_name: str):
    """Get tasks assigned to a specific agent"""
    try:
        db_manager = get_db_manager()
        
        # Get tasks for the specific agent
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    task_id, title, description, status, priority,
                    created_at, updated_at, completed_at
                FROM tasks 
                WHERE assigned_to = ?
                ORDER BY created_at DESC
                LIMIT 50
            """, (agent_name,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "task_id": row['task_id'],
                    "title": row['title'],
                    "description": row['description'],
                    "status": row['status'],
                    "priority": row['priority'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "completed_at": row['completed_at']
                })
            
            return {
                "agent_name": agent_name,
                "tasks": tasks,
                "task_count": len(tasks),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent tasks: {str(e)}")


@router.get("/{agent_name}/messages")
async def get_agent_messages(agent_name: str, limit: int = 50):
    """Get recent messages for a specific agent"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    message_id, from_bee, to_bee, message_type, subject, content,
                    priority, processed, created_at, sender_cli_used
                FROM bee_messages 
                WHERE from_bee = ? OR to_bee = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (agent_name, agent_name, limit))
            
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
                "agent_name": agent_name,
                "messages": messages,
                "message_count": len(messages),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent messages: {str(e)}")


@router.post("/{agent_name}/heartbeat")
async def update_agent_heartbeat(agent_name: str):
    """Update agent heartbeat (for health monitoring)"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE bee_states 
                SET last_heartbeat = CURRENT_TIMESTAMP,
                    last_activity = CURRENT_TIMESTAMP
                WHERE bee_name = ?
            """, (agent_name,))
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
            
            conn.commit()
            
            return {
                "message": f"Heartbeat updated for agent '{agent_name}'",
                "timestamp": datetime.now().isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update heartbeat: {str(e)}")