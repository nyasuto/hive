#!/usr/bin/env python3
"""
Beehive Web Dashboard - FastAPI Main Application
"""

import os
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .models.schemas import (
    AgentListResponse, TaskListResponse, MessageListResponse,
    InstructionRequest, InstructionResponse, TaskCreateRequest,
    SystemHealthResponse, ConversationStatsResponse, DashboardSummary,
    ErrorResponse
)
from .database.connection import get_db_manager
from .api import agents, tasks, instructions
from .websocket.manager import websocket_manager


# FastAPI app initialization
app = FastAPI(
    title="Beehive Web Dashboard API",
    description="Web API for Claude Multi-Agent Development System (Beehive)",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(instructions.router, prefix="/api/instructions", tags=["instructions"])

# Mount WebSocket manager
app.mount("/ws", websocket_manager.app)

# Project root for beehive.sh access
PROJECT_ROOT = Path(__file__).parent.parent.parent


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now()
        ).dict()
    )


@app.get("/api/health", response_model=SystemHealthResponse)
async def get_system_health():
    """Get overall system health status"""
    try:
        db_manager = get_db_manager()
        
        # Check database connection
        db_healthy = db_manager.check_database_health()
        
        # Check tmux session
        tmux_active = False
        try:
            result = subprocess.run(
                ["tmux", "has-session", "-t", "beehive"],
                capture_output=True,
                timeout=5
            )
            tmux_active = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            tmux_active = False
        
        # Check agent responsiveness (simplified - check last heartbeat)
        agents_responsive = {}
        if db_healthy:
            agents = db_manager.get_agents_status()
            current_time = datetime.now()
            
            for agent in agents:
                # Consider agent responsive if heartbeat within last 5 minutes
                time_diff = (current_time - agent.last_heartbeat).total_seconds()
                agents_responsive[agent.name.value] = time_diff < 300
        
        # Get active tasks count
        active_tasks_count = 0
        pending_messages_count = 0
        
        if db_healthy:
            tasks, _ = db_manager.get_tasks(limit=1000)  # Get all for counting
            active_tasks_count = len([t for t in tasks if t.status.value in ['pending', 'in_progress']])
            
            messages, _ = db_manager.get_messages(limit=1000)
            pending_messages_count = len([m for m in messages if not m.processed])
        
        # Determine overall status
        if db_healthy and tmux_active and any(agents_responsive.values()):
            status = "overall"
        elif db_healthy and (tmux_active or any(agents_responsive.values())):
            status = "degraded"
        else:
            status = "error"
        
        return SystemHealthResponse(
            status=status,
            tmux_session_active=tmux_active,
            database_connection=db_healthy,
            agents_responsive=agents_responsive,
            active_tasks_count=active_tasks_count,
            pending_messages_count=pending_messages_count,
            uptime_seconds=0.0,  # TODO: Implement proper uptime tracking
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/api/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats():
    """Get conversation statistics"""
    try:
        db_manager = get_db_manager()
        stats = db_manager.get_conversation_stats()
        
        return ConversationStatsResponse(
            total_messages=stats['total_messages'],
            beekeeper_instructions=stats['beekeeper_instructions'],
            bee_conversations=stats['bee_conversations'],
            sender_cli_usage_rate=stats['sender_cli_usage_rate'],
            active_conversations=stats['active_conversations'],
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")


@app.get("/api/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary():
    """Get complete dashboard summary"""
    try:
        db_manager = get_db_manager()
        
        # Get all dashboard data
        agents = db_manager.get_agents_status()
        recent_tasks, _ = db_manager.get_tasks(limit=10)
        recent_messages, _ = db_manager.get_messages(limit=20)
        
        # Get system health and stats
        system_health = await get_system_health()
        conversation_stats = await get_conversation_stats()
        
        return DashboardSummary(
            agents=agents,
            recent_tasks=recent_tasks,
            recent_messages=recent_messages,
            system_health=system_health,
            conversation_stats=conversation_stats,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard summary failed: {str(e)}")


async def execute_beehive_command(command: str, args: list = None) -> Dict[str, Any]:
    """Execute beehive.sh command asynchronously"""
    if args is None:
        args = []
    
    try:
        cmd = [str(PROJECT_ROOT / "beehive.sh"), command] + args
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "return_code": process.returncode
        }
        
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "return_code": -1
        }


@app.post("/api/system/init")
async def initialize_system(background_tasks: BackgroundTasks):
    """Initialize the beehive system"""
    try:
        result = await execute_beehive_command("init")
        
        if result["success"]:
            # Notify WebSocket clients about system initialization
            background_tasks.add_task(
                websocket_manager.broadcast_message,
                {
                    "type": "system_status",
                    "data": {"status": "initialized", "message": "System initialized successfully"},
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {"message": "System initialized successfully", "output": result["stdout"]}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"System initialization failed: {result['stderr']}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System initialization error: {str(e)}")


@app.post("/api/system/stop")
async def stop_system(background_tasks: BackgroundTasks):
    """Stop the beehive system"""
    try:
        result = await execute_beehive_command("stop")
        
        if result["success"]:
            # Notify WebSocket clients about system shutdown
            background_tasks.add_task(
                websocket_manager.broadcast_message,
                {
                    "type": "system_status", 
                    "data": {"status": "stopped", "message": "System stopped successfully"},
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return {"message": "System stopped successfully", "output": result["stdout"]}
        else:
            raise HTTPException(
                status_code=500,
                detail=f"System stop failed: {result['stderr']}"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System stop error: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    print("🐝 Beehive Web Dashboard API starting up...")
    
    # Initialize WebSocket manager
    await websocket_manager.startup()
    
    print("✅ Beehive Web Dashboard API ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    print("🛑 Beehive Web Dashboard API shutting down...")
    
    # Cleanup WebSocket connections
    await websocket_manager.shutdown()
    
    print("✅ Beehive Web Dashboard API shut down gracefully!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )