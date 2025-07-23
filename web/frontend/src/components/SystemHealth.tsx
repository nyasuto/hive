// System Health Component

import React from 'react';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Database, 
  Terminal, 
  Users, 
  Clock,
  Activity
} from 'lucide-react';
import { SystemHealth } from '../types';
import { formatRelativeTime } from '../services/api';

interface SystemHealthProps {
  health: SystemHealth;
}

const SystemHealthComponent: React.FC<SystemHealthProps> = ({ health }) => {
  const getOverallStatusColor = (status: string) => {
    switch (status) {
      case 'overall':
        return {
          bg: 'bg-emerald-50',
          border: 'border-emerald-200',
          text: 'text-emerald-800',
          icon: CheckCircle,
          color: 'text-emerald-500'
        };
      case 'degraded':
        return {
          bg: 'bg-amber-50',
          border: 'border-amber-200',
          text: 'text-amber-800',
          icon: AlertTriangle,
          color: 'text-amber-500'
        };
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          text: 'text-red-800',
          icon: XCircle,
          color: 'text-red-500'
        };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          text: 'text-gray-800',
          icon: AlertTriangle,
          color: 'text-gray-500'
        };
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'overall':
        return '正常';
      case 'degraded':
        return '一部に問題';
      case 'error':
        return 'エラー';
      default:
        return '不明';
    }
  };

  const getHealthIcon = (isHealthy: boolean) => {
    return isHealthy ? (
      <CheckCircle className="h-4 w-4 text-emerald-500" />
    ) : (
      <XCircle className="h-4 w-4 text-red-500" />
    );
  };

  const overallStatus = getOverallStatusColor(health.status);
  const StatusIcon = overallStatus.icon;

  // Calculate uptime display
  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}秒`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}分`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}時間`;
    return `${Math.round(seconds / 86400)}日`;
  };

  const activeAgentsCount = Object.values(health.agents_responsive).filter(Boolean).length;
  const totalAgentsCount = Object.keys(health.agents_responsive).length;

  return (
    <div className={`card p-6 ${overallStatus.bg} ${overallStatus.border}`}>
      {/* Overall Status Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <StatusIcon className={`h-6 w-6 ${overallStatus.color} mr-3`} />
          <div>
            <h2 className="text-lg font-semibold text-gray-900">システム状態</h2>
            <p className={`text-sm ${overallStatus.text}`}>
              {getStatusText(health.status)}
            </p>
          </div>
        </div>
        
        <div className="text-right">
          <div className="text-sm text-gray-500">最終更新</div>
          <div className="text-sm font-medium text-gray-900">
            {formatRelativeTime(health.timestamp)}
          </div>
        </div>
      </div>

      {/* Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Database Connection */}
        <div className="flex items-center p-3 bg-white rounded-lg border border-gray-200">
          <Database className="h-5 w-5 mr-3 text-gray-600" />
          <div>
            <div className="flex items-center">
              {getHealthIcon(health.database_connection)}
              <span className="ml-2 text-sm font-medium text-gray-900">
                データベース
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {health.database_connection ? '接続中' : '切断'}
            </div>
          </div>
        </div>

        {/* Tmux Session */}
        <div className="flex items-center p-3 bg-white rounded-lg border border-gray-200">
          <Terminal className="h-5 w-5 mr-3 text-gray-600" />
          <div>
            <div className="flex items-center">
              {getHealthIcon(health.tmux_session_active)}
              <span className="ml-2 text-sm font-medium text-gray-900">
                Tmuxセッション
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {health.tmux_session_active ? 'アクティブ' : '非アクティブ'}
            </div>
          </div>
        </div>

        {/* Active Agents */}
        <div className="flex items-center p-3 bg-white rounded-lg border border-gray-200">
          <Users className="h-5 w-5 mr-3 text-gray-600" />
          <div>
            <div className="flex items-center">
              {getHealthIcon(activeAgentsCount > 0)}
              <span className="ml-2 text-sm font-medium text-gray-900">
                エージェント
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {activeAgentsCount}/{totalAgentsCount} アクティブ
            </div>
          </div>
        </div>

        {/* System Uptime */}
        <div className="flex items-center p-3 bg-white rounded-lg border border-gray-200">
          <Clock className="h-5 w-5 mr-3 text-gray-600" />
          <div>
            <div className="flex items-center">
              <Activity className="h-4 w-4 text-blue-500" />
              <span className="ml-2 text-sm font-medium text-gray-900">
                稼働時間
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {formatUptime(health.uptime_seconds)}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Agent Status */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-900">エージェント詳細状態</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Object.entries(health.agents_responsive).map(([agentName, isResponsive]) => {
            const agentDisplayNames: Record<string, string> = {
              queen: '👑 Queen Bee',
              developer: '💻 Developer',
              qa: '🧪 QA',
              analyst: '📊 Analyst'
            };

            return (
              <div
                key={agentName}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200"
              >
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-900">
                    {agentDisplayNames[agentName] || agentName}
                  </span>
                </div>
                
                <div className="flex items-center">
                  {getHealthIcon(isResponsive)}
                  <span className={`ml-2 text-xs ${isResponsive ? 'text-emerald-600' : 'text-red-600'}`}>
                    {isResponsive ? '応答中' : '応答なし'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Activity Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">アクティブタスク</span>
            <span className="text-sm font-medium text-gray-900">
              {health.active_tasks_count} 件
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">未処理メッセージ</span>
            <span className="text-sm font-medium text-gray-900">
              {health.pending_messages_count} 件
            </span>
          </div>
        </div>
      </div>

      {/* Status Indicators */}
      <div className="mt-4 flex items-center justify-center space-x-4 text-xs text-gray-500">
        <div className="flex items-center">
          <div className="w-2 h-2 bg-emerald-500 rounded-full mr-1"></div>
          正常
        </div>
        <div className="flex items-center">
          <div className="w-2 h-2 bg-amber-500 rounded-full mr-1"></div>
          警告
        </div>
        <div className="flex items-center">
          <div className="w-2 h-2 bg-red-500 rounded-full mr-1"></div>
          エラー
        </div>
      </div>
    </div>
  );
};

export default SystemHealthComponent;