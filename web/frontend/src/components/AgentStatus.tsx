// Agent Status Component

import React from 'react';
import { User, Clock, Zap, TrendingUp, Activity } from 'lucide-react';
import { Agent } from '../types';
import { formatRelativeTime, getAgentDisplayName, getStatusColor } from '../services/api';

interface AgentStatusProps {
  agents: Agent[];
}

const AgentStatus: React.FC<AgentStatusProps> = ({ agents }) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'busy':
        return <div className="status-busy" />;
      case 'waiting':
        return <div className="status-waiting" />;
      case 'offline':
        return <div className="status-offline" />;
      case 'error':
        return <div className="status-error" />;
      default:
        return <div className="status-idle" />;
    }
  };

  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      idle: 'アイドル',
      busy: '作業中',
      waiting: '待機中',
      offline: 'オフライン',
      error: 'エラー'
    };
    return statusMap[status] || status;
  };

  const getAgentIcon = (agentType: string) => {
    const iconMap: Record<string, string> = {
      queen: '👑',
      developer: '💻',
      qa: '🧪',
      analyst: '📊'
    };
    return iconMap[agentType] || '🐝';
  };

  if (agents.length === 0) {
    return (
      <div className="card p-8 text-center">
        <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500">エージェント情報が見つかりません</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {agents.map((agent) => (
        <div key={agent.name} className={`card p-6 agent-${agent.name}`}>
          {/* Agent Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <div className="text-2xl mr-3">
                {getAgentIcon(agent.name)}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {getAgentDisplayName(agent.name)}
                </h3>
                <div className="flex items-center mt-1">
                  {getStatusIcon(agent.status)}
                  <span className={`ml-2 text-sm font-medium ${getStatusColor(agent.status)}`}>
                    {getStatusText(agent.status)}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Performance Score */}
            <div className="text-right">
              <div className="text-sm text-gray-500">パフォーマンス</div>
              <div className="text-lg font-bold text-emerald-600">
                {Math.round(agent.performance_score)}%
              </div>
            </div>
          </div>

          {/* Current Task */}
          {agent.current_task_title && (
            <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <div className="flex items-center text-amber-800">
                <Activity className="h-4 w-4 mr-2" />
                <span className="text-sm font-medium">現在のタスク</span>
              </div>
              <p className="text-sm text-amber-700 mt-1 truncate">
                {agent.current_task_title}
              </p>
            </div>
          )}

          {/* Agent Metrics */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="text-center">
              <div className="flex items-center justify-center text-blue-600 mb-1">
                <TrendingUp className="h-4 w-4 mr-1" />
                <span className="text-xs text-gray-500">負荷</span>
              </div>
              <div className="text-sm font-semibold">
                {Math.round(agent.workload_score)}%
              </div>
            </div>
            
            <div className="text-center">
              <div className="flex items-center justify-center text-purple-600 mb-1">
                <Zap className="h-4 w-4 mr-1" />
                <span className="text-xs text-gray-500">能力</span>
              </div>
              <div className="text-sm font-semibold">
                {agent.capabilities.length}
              </div>
            </div>
          </div>

          {/* Last Activity */}
          <div className="flex items-center text-gray-500 text-sm">
            <Clock className="h-4 w-4 mr-2" />
            <span>
              最終活動: {formatRelativeTime(agent.last_activity)}
            </span>
          </div>

          {/* Capabilities */}
          {agent.capabilities.length > 0 && (
            <div className="mt-4">
              <div className="text-xs text-gray-500 mb-2">機能</div>
              <div className="flex flex-wrap gap-1">
                {agent.capabilities.slice(0, 3).map((capability, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                  >
                    {capability}
                  </span>
                ))}
                {agent.capabilities.length > 3 && (
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                    +{agent.capabilities.length - 3}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Heartbeat Indicator */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>ハートビート</span>
              <span>{formatRelativeTime(agent.last_heartbeat)}</span>
            </div>
            <div className="mt-1 w-full bg-gray-200 rounded-full h-1">
              <div 
                className={`h-1 rounded-full transition-all duration-300 ${
                  new Date().getTime() - new Date(agent.last_heartbeat).getTime() < 300000
                    ? 'bg-emerald-500' 
                    : 'bg-red-500'
                }`}
                style={{ 
                  width: new Date().getTime() - new Date(agent.last_heartbeat).getTime() < 300000 
                    ? '100%' 
                    : '20%' 
                }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AgentStatus;