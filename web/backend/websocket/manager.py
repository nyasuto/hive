#!/usr/bin/env python3
"""
WebSocket Manager for Beehive Web Dashboard
Handles real-time communication between backend and frontend
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect, FastAPI
from fastapi.websockets import WebSocketState

from database.connection import get_db_manager


class WebSocketManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.app = FastAPI()
        self.logger = logging.getLogger(__name__)
        self._monitoring_task: asyncio.Task = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup WebSocket routes"""
        
        @self.app.websocket("/")
        async def websocket_endpoint(websocket: WebSocket):
            await self.connect(websocket)
            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self.handle_client_message(websocket, message)
                    
            except WebSocketDisconnect:
                await self.disconnect(websocket)
            except Exception as e:
                self.logger.error(f"WebSocket error: {str(e)}")
                await self.disconnect(websocket)
    
    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
        
        # Send initial system status
        await self.send_system_status(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to send personal message: {str(e)}")
                await self.disconnect(websocket)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections.copy():
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message_json)
                else:
                    disconnected.add(connection)
            except Exception as e:
                self.logger.error(f"Failed to broadcast to connection: {str(e)}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def handle_client_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle messages from clients"""
        try:
            message_type = message.get('type')
            
            if message_type == 'ping':
                await self.send_personal_message({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }, websocket)
            
            elif message_type == 'subscribe':
                # Handle subscription to specific data types
                subscription = message.get('subscription', 'all')
                await self.handle_subscription(websocket, subscription)
            
            elif message_type == 'request_status':
                # Send current system status
                await self.send_system_status(websocket)
            
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            self.logger.error(f"Error handling client message: {str(e)}")
    
    async def handle_subscription(self, websocket: WebSocket, subscription: str):
        """Handle client subscription requests"""
        try:
            db_manager = get_db_manager()
            
            if subscription == 'agents' or subscription == 'all':
                agents = db_manager.get_agents_status()
                await self.send_personal_message({
                    'type': 'agent_status',
                    'data': {
                        'agents': [agent.dict() for agent in agents],
                        'timestamp': datetime.now().isoformat()
                    }
                }, websocket)
            
            if subscription == 'tasks' or subscription == 'all':
                tasks, _ = db_manager.get_tasks(limit=20)
                await self.send_personal_message({
                    'type': 'task_update',
                    'data': {
                        'tasks': [task.dict() for task in tasks],
                        'timestamp': datetime.now().isoformat()
                    }
                }, websocket)
                
        except Exception as e:
            self.logger.error(f"Error handling subscription: {str(e)}")
    
    async def send_system_status(self, websocket: WebSocket):
        """Send current system status to client"""
        try:
            # This would typically call the health endpoint logic
            status_data = {
                'type': 'system_status',
                'data': {
                    'connected': True,
                    'timestamp': datetime.now().isoformat(),
                    'connection_count': len(self.active_connections)
                }
            }
            await self.send_personal_message(status_data, websocket)
            
        except Exception as e:
            self.logger.error(f"Error sending system status: {str(e)}")
    
    async def start_monitoring(self):
        """Start background monitoring for real-time updates"""
        if self._monitoring_task is not None:
            return
        
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("WebSocket monitoring started")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None
            self.logger.info("WebSocket monitoring stopped")
    
    async def _monitoring_loop(self):
        """Background loop for monitoring system changes"""
        last_check = datetime.now()
        
        try:
            while True:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                if not self.active_connections:
                    continue
                
                try:
                    # Check for system changes since last check
                    current_time = datetime.now()
                    
                    # Get recent changes (simplified - could be enhanced with change detection)
                    db_manager = get_db_manager()
                    
                    # Check for agent status changes
                    agents = db_manager.get_agents_status()
                    await self.broadcast_message({
                        'type': 'agent_status_update',
                        'data': {
                            'agents': [agent.dict() for agent in agents],
                            'timestamp': current_time.isoformat()
                        }
                    })
                    
                    # Check for new tasks/messages (simplified)
                    tasks, _ = db_manager.get_tasks(limit=10)
                    recent_tasks = [
                        task for task in tasks 
                        if task.updated_at > last_check
                    ]
                    
                    if recent_tasks:
                        await self.broadcast_message({
                            'type': 'task_update',
                            'data': {
                                'tasks': [task.dict() for task in recent_tasks],
                                'timestamp': current_time.isoformat()
                            }
                        })
                    
                    last_check = current_time
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {str(e)}")
                    
        except asyncio.CancelledError:
            self.logger.info("Monitoring loop cancelled")
            raise
    
    async def startup(self):
        """Initialize WebSocket manager"""
        self.logger.info("WebSocket manager starting up")
        await self.start_monitoring()
    
    async def shutdown(self):
        """Cleanup WebSocket manager"""
        self.logger.info("WebSocket manager shutting down")
        
        # Stop monitoring
        await self.stop_monitoring()
        
        # Close all connections
        disconnected = []
        for connection in self.active_connections.copy():
            try:
                await connection.close()
                disconnected.append(connection)
            except Exception as e:
                self.logger.error(f"Error closing connection: {str(e)}")
        
        for connection in disconnected:
            self.active_connections.discard(connection)
        
        self.logger.info("All WebSocket connections closed")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    async def notify_agent_status_change(self, agent_name: str, status: str):
        """Notify clients of agent status change"""
        await self.broadcast_message({
            'type': 'agent_status_change',
            'data': {
                'agent_name': agent_name,
                'new_status': status,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    async def notify_task_creation(self, task_data: Dict[str, Any]):
        """Notify clients of new task creation"""
        await self.broadcast_message({
            'type': 'task_created',
            'data': {
                'task': task_data,
                'timestamp': datetime.now().isoformat()
            }
        })
    
    async def notify_instruction_sent(self, instruction_data: Dict[str, Any]):
        """Notify clients of instruction sent"""
        await self.broadcast_message({
            'type': 'instruction_sent',
            'data': {
                'instruction': instruction_data,
                'timestamp': datetime.now().isoformat()
            }
        })


# Singleton instance
websocket_manager = WebSocketManager()