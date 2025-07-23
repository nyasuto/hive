#!/usr/bin/env python3
"""
Instructions API endpoints for Beehive Web Dashboard
"""

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models.schemas import InstructionRequest, InstructionResponse
from ..database.connection import get_db_manager

router = APIRouter()

# Project root for beehive.sh access
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@router.post("/", response_model=InstructionResponse)
async def send_instruction(
    instruction: InstructionRequest,
    background_tasks: BackgroundTasks
):
    """Send instruction to agent(s) via beehive system"""
    try:
        db_manager = get_db_manager()
        
        # Validate target agent
        target_agent = instruction.target_agent
        if isinstance(target_agent, str):
            if target_agent not in ['queen', 'developer', 'qa', 'analyst', 'all']:
                raise HTTPException(status_code=400, detail="Invalid target agent")
        else:
            target_agent = target_agent.value
        
        # Store instruction in database
        instruction_data = {
            'content': instruction.content,
            'target_agent': target_agent,
            'priority': instruction.priority.value,
            'subject': instruction.subject or 'Web Dashboard Instruction'
        }
        
        instruction_id = db_manager.insert_beekeeper_instruction(instruction_data)
        
        # Create task if requested
        task_created = False
        task_id = None
        
        if instruction.create_task:
            # Check if instruction contains task keywords (simplified detection)
            task_keywords = ['実装', '開発', '作成', '修正', 'テスト', 'デバッグ', 
                           'implement', 'develop', 'create', 'fix', 'test', 'debug']
            
            if any(keyword in instruction.content.lower() for keyword in task_keywords):
                task_data = {
                    'title': instruction.content[:50] + ('...' if len(instruction.content) > 50 else ''),
                    'description': instruction.content,
                    'priority': instruction.priority.value,
                    'assigned_to': target_agent if target_agent != 'all' else None,
                    'created_by': 'web_dashboard',
                    'metadata': {
                        'auto_generated': True,
                        'instruction_id': instruction_id,
                        'created_via': 'web_dashboard'
                    }
                }
                
                task_id = db_manager.create_task(task_data)
                task_created = True
        
        # Send instruction via beehive.sh asynchronously
        background_tasks.add_task(
            execute_beehive_instruction,
            instruction.content,
            target_agent
        )
        
        return InstructionResponse(
            instruction_id=instruction_id,
            content=instruction.content,
            target_agent=target_agent,
            priority=instruction.priority,
            created_at=datetime.now(),
            task_created=task_created,
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send instruction: {str(e)}")


@router.get("/history")
async def get_instruction_history(limit: int = 50):
    """Get history of beekeeper instructions"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    message_id, to_bee, subject, content, priority, created_at
                FROM bee_messages 
                WHERE from_bee = 'beekeeper' AND message_type = 'instruction'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            instructions = []
            for row in cursor.fetchall():
                instructions.append({
                    "instruction_id": row['message_id'],
                    "target_agent": row['to_bee'],
                    "subject": row['subject'],
                    "content": row['content'],
                    "priority": row['priority'],
                    "created_at": row['created_at']
                })
            
            return {
                "instructions": instructions,
                "count": len(instructions),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get instruction history: {str(e)}")


@router.get("/{instruction_id}")
async def get_instruction(instruction_id: int):
    """Get a specific instruction by ID"""
    try:
        db_manager = get_db_manager()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    message_id, from_bee, to_bee, message_type, subject, content,
                    priority, processed, processed_at, created_at
                FROM bee_messages 
                WHERE message_id = ? AND from_bee = 'beekeeper'
            """, (instruction_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Instruction '{instruction_id}' not found")
            
            return {
                "instruction_id": row['message_id'],
                "from_bee": row['from_bee'],
                "target_agent": row['to_bee'],
                "message_type": row['message_type'],
                "subject": row['subject'],
                "content": row['content'],
                "priority": row['priority'],
                "processed": bool(row['processed']),
                "processed_at": row['processed_at'],
                "created_at": row['created_at']
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get instruction: {str(e)}")


async def execute_beehive_instruction(content: str, target_agent: str):
    """Execute beehive instruction asynchronously"""
    try:
        # Use beehive.sh start-task command to send instruction
        cmd = [
            str(PROJECT_ROOT / "beehive.sh"),
            "start-task",
            content
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT
        )
        
        stdout, stderr = await process.communicate()
        
        # Log the result (could be enhanced with proper logging)
        if process.returncode == 0:
            print(f"✅ Instruction sent successfully: {content[:50]}...")
        else:
            print(f"❌ Instruction failed: {stderr.decode()}")
            
    except Exception as e:
        print(f"❌ Error executing instruction: {str(e)}")


@router.get("/templates/")
async def get_instruction_templates():
    """Get pre-defined instruction templates"""
    templates = [
        {
            "id": "implement_feature",
            "name": "機能実装",
            "template": "{feature_name}を実装してください。要件：{requirements}",
            "variables": ["feature_name", "requirements"],
            "target_agent": "developer",
            "priority": "medium"
        },
        {
            "id": "fix_bug",
            "name": "バグ修正",
            "template": "{bug_description}のバグを修正してください。再現手順：{reproduction_steps}",
            "variables": ["bug_description", "reproduction_steps"],
            "target_agent": "developer",
            "priority": "high"
        },
        {
            "id": "run_tests",
            "name": "テスト実行",
            "template": "{test_scope}のテストを実行してください。確認項目：{test_items}",
            "variables": ["test_scope", "test_items"],
            "target_agent": "qa",
            "priority": "medium"
        },
        {
            "id": "code_review",
            "name": "コードレビュー",
            "template": "{code_location}のコードレビューをお願いします。重点チェック項目：{review_points}",
            "variables": ["code_location", "review_points"],
            "target_agent": "qa",
            "priority": "medium"
        },
        {
            "id": "analyze_performance",
            "name": "パフォーマンス分析",
            "template": "{target_component}のパフォーマンス分析を実行してください。観点：{analysis_focus}",
            "variables": ["target_component", "analysis_focus"],
            "target_agent": "analyst",
            "priority": "low"
        },
        {
            "id": "status_check",
            "name": "進捗確認",
            "template": "{task_name}の進捗状況を教えてください。",
            "variables": ["task_name"],
            "target_agent": "all",
            "priority": "low"
        }
    ]
    
    return {
        "templates": templates,
        "count": len(templates),
        "timestamp": datetime.now().isoformat()
    }