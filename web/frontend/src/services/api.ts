// API service for Beehive Web Dashboard

import axios, { AxiosResponse } from 'axios';
import {
  Agent,
  Task,
  Message,
  SystemHealth,
  ConversationStats,
  DashboardSummary,
  InstructionRequest,
  InstructionResponse,
  TaskCreateRequest,
  InstructionTemplate,
  AgentListResponse,
  TaskListResponse,
  MessageListResponse
} from '../types';

const API_BASE = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`🔗 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('❌ API Response Error:', error.response?.data || error.message);
    
    // Handle common error cases
    if (error.response?.status === 404) {
      throw new Error('リソースが見つかりません');
    } else if (error.response?.status === 500) {
      throw new Error('サーバーエラーが発生しました');
    } else if (error.code === 'ECONNABORTED') {
      throw new Error('リクエストがタイムアウトしました');
    } else if (!error.response) {
      throw new Error('サーバーに接続できません');
    }
    
    return Promise.reject(error);
  }
);

// Agents API
export const agentsApi = {
  getAll: async (): Promise<AgentListResponse> => {
    const response: AxiosResponse<AgentListResponse> = await api.get('/agents/');
    return response.data;
  },

  getAgent: async (agentName: string): Promise<Agent> => {
    const response: AxiosResponse<Agent> = await api.get(`/agents/${agentName}`);
    return response.data;
  },

  getAgentTasks: async (agentName: string) => {
    const response = await api.get(`/agents/${agentName}/tasks`);
    return response.data;
  },

  getAgentMessages: async (agentName: string, limit: number = 50) => {
    const response = await api.get(`/agents/${agentName}/messages`, {
      params: { limit }
    });
    return response.data;
  },

  updateHeartbeat: async (agentName: string) => {
    const response = await api.post(`/agents/${agentName}/heartbeat`);
    return response.data;
  }
};

// Tasks API
export const tasksApi = {
  getAll: async (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    assigned_to?: string;
  }): Promise<TaskListResponse> => {
    const response: AxiosResponse<TaskListResponse> = await api.get('/tasks/', { params });
    return response.data;
  },

  getTask: async (taskId: string): Promise<Task> => {
    const response: AxiosResponse<Task> = await api.get(`/tasks/${taskId}`);
    return response.data;
  },

  createTask: async (taskData: TaskCreateRequest) => {
    const response = await api.post('/tasks/', taskData);
    return response.data;
  },

  updateTaskStatus: async (taskId: string, status: string) => {
    const response = await api.put(`/tasks/${taskId}/status`, null, {
      params: { status }
    });
    return response.data;
  },

  assignTask: async (taskId: string, agentName: string) => {
    const response = await api.put(`/tasks/${taskId}/assign`, null, {
      params: { agent_name: agentName }
    });
    return response.data;
  },

  getTaskMessages: async (taskId: string) => {
    const response = await api.get(`/tasks/${taskId}/messages`);
    return response.data;
  },

  deleteTask: async (taskId: string) => {
    const response = await api.delete(`/tasks/${taskId}`);
    return response.data;
  }
};

// Instructions API
export const instructionsApi = {
  sendInstruction: async (instruction: InstructionRequest): Promise<InstructionResponse> => {
    const response: AxiosResponse<InstructionResponse> = await api.post('/instructions/', instruction);
    return response.data;
  },

  getHistory: async (limit: number = 50) => {
    const response = await api.get('/instructions/history', {
      params: { limit }
    });
    return response.data;
  },

  getInstruction: async (instructionId: number) => {
    const response = await api.get(`/instructions/${instructionId}`);
    return response.data;
  },

  getTemplates: async (): Promise<{ templates: InstructionTemplate[] }> => {
    const response = await api.get('/instructions/templates/');
    return response.data;
  }
};

// System API
export const systemApi = {
  getHealth: async (): Promise<SystemHealth> => {
    const response: AxiosResponse<SystemHealth> = await api.get('/health');
    return response.data;
  },

  getStats: async (): Promise<ConversationStats> => {
    const response: AxiosResponse<ConversationStats> = await api.get('/stats');
    return response.data;
  },

  getDashboard: async (): Promise<DashboardSummary> => {
    const response: AxiosResponse<DashboardSummary> = await api.get('/dashboard');
    return response.data;
  },

  initSystem: async () => {
    const response = await api.post('/system/init');
    return response.data;
  },

  stopSystem: async () => {
    const response = await api.post('/system/stop');
    return response.data;
  }
};

// Helper functions
export const formatTimestamp = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

export const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  const diffMs = now.getTime() - time.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) {
    return 'たった今';
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分前`;
  } else if (diffHours < 24) {
    return `${diffHours}時間前`;
  } else {
    return `${diffDays}日前`;
  }
};

export const getAgentDisplayName = (agentType: string): string => {
  const names: Record<string, string> = {
    queen: 'Queen Bee',
    developer: 'Developer',
    qa: 'QA',
    analyst: 'Analyst'
  };
  return names[agentType] || agentType;
};

export const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    idle: 'text-gray-500',
    busy: 'text-amber-500',
    waiting: 'text-blue-500',
    offline: 'text-gray-400',
    error: 'text-red-500',
    pending: 'text-blue-500',
    in_progress: 'text-amber-500',
    completed: 'text-emerald-500',
    failed: 'text-red-500',
    cancelled: 'text-gray-500'
  };
  return colors[status] || 'text-gray-500';
};

export const getPriorityColor = (priority: string): string => {
  const colors: Record<string, string> = {
    low: 'text-green-600 bg-green-100',
    medium: 'text-blue-600 bg-blue-100',
    high: 'text-amber-600 bg-amber-100',
    critical: 'text-red-600 bg-red-100'
  };
  return colors[priority] || 'text-gray-600 bg-gray-100';
};

export default api;