// TypeScript type definitions for Beehive Web Dashboard

export type AgentType = 'queen' | 'developer' | 'qa' | 'analyst';

export type AgentStatus = 'idle' | 'busy' | 'waiting' | 'offline' | 'error';

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';

export type Priority = 'low' | 'medium' | 'high' | 'critical';

export type MessageType = 'info' | 'question' | 'request' | 'response' | 'alert' | 'task_update' | 'instruction' | 'conversation';

export interface Agent {
  name: AgentType;
  status: AgentStatus;
  current_task_id?: string;
  current_task_title?: string;
  last_activity: string;
  last_heartbeat: string;
  workload_score: number;
  performance_score: number;
  capabilities: string[];
  metadata: Record<string, any>;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  estimated_hours?: number;
  actual_hours?: number;
  created_by: string;
  metadata: Record<string, any>;
}

export interface Message {
  message_id: number;
  from_bee: string;
  to_bee: string;
  message_type: MessageType;
  subject?: string;
  content: string;
  task_id?: string;
  priority: Priority;
  processed: boolean;
  processed_at?: string;
  created_at: string;
  sender_cli_used: boolean;
  conversation_id?: string;
}

export interface SystemHealth {
  status: 'overall' | 'degraded' | 'error';
  tmux_session_active: boolean;
  database_connection: boolean;
  agents_responsive: Record<string, boolean>;
  active_tasks_count: number;
  pending_messages_count: number;
  uptime_seconds: number;
  timestamp: string;
}

export interface ConversationStats {
  total_messages: number;
  beekeeper_instructions: number;
  bee_conversations: number;
  sender_cli_usage_rate: number;
  active_conversations: number;
  timestamp: string;
}

export interface InstructionRequest {
  content: string;
  target_agent: AgentType | 'all';
  priority: Priority;
  create_task: boolean;
  subject?: string;
}

export interface InstructionResponse {
  instruction_id: number;
  content: string;
  target_agent: string;
  priority: Priority;
  created_at: string;
  task_created: boolean;
  task_id?: string;
}

export interface TaskCreateRequest {
  title: string;
  description: string;
  priority: Priority;
  assigned_to?: AgentType;
  estimated_hours?: number;
}

export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface DashboardSummary {
  agents: Agent[];
  recent_tasks: Task[];
  recent_messages: Message[];  
  system_health: SystemHealth;
  conversation_stats: ConversationStats;
  timestamp: string;
}

export interface InstructionTemplate {
  id: string;
  name: string;
  template: string;
  variables: string[];
  target_agent: string;
  priority: Priority;
}

// API Response types
export interface AgentListResponse {
  agents: Agent[];
  total_count: number;
  active_count: number;
  timestamp: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total_count: number;
  page: number;
  per_page: number;
  timestamp: string;
}

export interface MessageListResponse {
  messages: Message[];
  total_count: number;
  page: number;
  per_page: number;
  timestamp: string;
}

// UI State types
export interface AppState {
  isConnected: boolean;
  lastUpdate: string;
  systemHealth: SystemHealth | null;
  agents: Agent[];
  tasks: Task[];
  messages: Message[];
  conversationStats: ConversationStats | null;
}

export interface LoadingState {
  agents: boolean;
  tasks: boolean;
  messages: boolean;
  systemHealth: boolean;
  dashboard: boolean;
}

export interface ErrorState {
  agents: string | null;
  tasks: string | null;
  messages: string | null;
  systemHealth: string | null;
  general: string | null;
}