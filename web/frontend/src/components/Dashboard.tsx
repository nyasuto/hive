// Main Dashboard Component

import React, { useState, useEffect } from 'react';
import { Activity, Users, CheckSquare, MessageSquare, AlertTriangle, Wifi, WifiOff } from 'lucide-react';
import { systemApi } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { DashboardSummary, WebSocketMessage } from '../types';
import AgentStatus from './AgentStatus';
import TaskList from './TaskList';
import InstructionForm from './InstructionForm';
import SystemHealth from './SystemHealth';

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  
  const { isConnected, lastMessage, reconnect, connectionError } = useWebSocket('ws://localhost:8000/ws/');

  // Load initial dashboard data
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await systemApi.getDashboard();
      setDashboardData(data);
      setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'データの読み込みに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    const message: WebSocketMessage = lastMessage;
    
    switch (message.type) {
      case 'agent_status_update':
        if (dashboardData) {
          setDashboardData(prev => prev ? {
            ...prev,
            agents: message.data.agents,
            timestamp: message.timestamp
          } : null);
        }
        break;
        
      case 'task_update':
        if (dashboardData && message.data.tasks) {
          setDashboardData(prev => prev ? {
            ...prev,
            recent_tasks: message.data.tasks,
            timestamp: message.timestamp
          } : null);
        }
        break;
        
      case 'system_status':
        console.log('System status update:', message.data);
        break;
        
      case 'pong':
        // Handle ping response
        break;
        
      default:
        console.log('Unknown WebSocket message type:', message.type);
    }
    
    setLastUpdate(new Date().toLocaleTimeString('ja-JP'));
  }, [lastMessage, dashboardData]);

  // Initial load
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Auto-refresh every 30 seconds if not connected to WebSocket
  useEffect(() => {
    if (isConnected) return;

    const interval = setInterval(() => {
      loadDashboardData();
    }, 30000);

    return () => clearInterval(interval);
  }, [isConnected]);

  if (loading && !dashboardData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-hive-primary mx-auto"></div>
          <p className="mt-4 text-gray-600">ダッシュボードを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error && !dashboardData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
          <p className="mt-4 text-red-600">{error}</p>
          <button
            onClick={loadDashboardData}
            className="mt-4 btn-primary"
          >
            再試行
          </button>
        </div>
      </div>
    );
  }

  const stats = [
    {
      title: 'アクティブエージェント',
      value: dashboardData?.agents.filter(a => a.status !== 'offline').length || 0,
      total: dashboardData?.agents.length || 0,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      title: 'アクティブタスク',
      value: dashboardData?.system_health.active_tasks_count || 0,
      icon: CheckSquare,
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-100'
    },
    {
      title: '未処理メッセージ',
      value: dashboardData?.system_health.pending_messages_count || 0,
      icon: MessageSquare,
      color: 'text-amber-600',
      bgColor: 'bg-amber-100'
    },
    {
      title: '総会話数',
      value: dashboardData?.conversation_stats.total_messages || 0,
      icon: Activity,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100'
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-hive-primary rounded-lg flex items-center justify-center mr-3">
                  <span className="text-white font-bold">🐝</span>
                </div>
                <h1 className="text-2xl font-bold text-gray-900">Beehive Dashboard</h1>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className="flex items-center">
                {isConnected ? (
                  <div className="flex items-center text-emerald-600">
                    <Wifi className="h-4 w-4 mr-1" />
                    <span className="text-sm">接続中</span>
                  </div>
                ) : (
                  <div className="flex items-center text-red-600">
                    <WifiOff className="h-4 w-4 mr-1" />
                    <span className="text-sm">切断</span>
                    <button 
                      onClick={reconnect}
                      className="ml-2 text-xs btn-secondary py-1 px-2"
                    >
                      再接続
                    </button>
                  </div>
                )}
              </div>
              
              {/* Last Update */}
              <div className="text-sm text-gray-500">
                最終更新: {lastUpdate}
              </div>
              
              {/* Refresh Button */}
              <button
                onClick={loadDashboardData}
                disabled={loading}
                className="btn-secondary"
              >
                {loading ? '更新中...' : '更新'}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Connection Error */}
        {connectionError && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">接続エラー</h3>
                <p className="mt-1 text-sm text-red-700">{connectionError}</p>
              </div>
            </div>
          </div>
        )}

        {/* System Health */}
        {dashboardData?.system_health && (
          <div className="mb-8">
            <SystemHealth health={dashboardData.system_health} />
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <div key={index} className="card p-6">
              <div className="flex items-center">
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.title}</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stat.value}
                    {stat.total && (
                      <span className="text-lg text-gray-500">/{stat.total}</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Agents and Tasks */}
          <div className="lg:col-span-2 space-y-8">
            {/* Agent Status */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">エージェント状態</h2>
              <AgentStatus agents={dashboardData?.agents || []} />
            </div>

            {/* Recent Tasks */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">最近のタスク</h2>
              <TaskList tasks={dashboardData?.recent_tasks || []} showPagination={false} />
            </div>
          </div>

          {/* Right Column - Instruction Form and Messages */}
          <div className="space-y-8">
            {/* Instruction Form */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">指示投入</h2>
              <InstructionForm onInstructionSent={loadDashboardData} />
            </div>

            {/* Recent Messages */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">最近のメッセージ</h2>
              <div className="card">
                <div className="p-4 max-h-96 overflow-y-auto scrollbar-hide">
                  {dashboardData?.recent_messages.slice(0, 10).map((message) => (
                    <div key={message.message_id} className="mb-4 last:mb-0">
                      <div className="flex items-start space-x-3">
                        <div className="flex-shrink-0">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium agent-${message.from_bee}`}>
                            {message.from_bee.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <p className="text-sm font-medium text-gray-900">
                              {message.from_bee} → {message.to_bee}
                            </p>
                            <span className={`badge ${message.processed ? 'badge-success' : 'badge-warning'}`}>
                              {message.processed ? '処理済み' : '未処理'}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1 truncate">
                            {message.content}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {new Date(message.created_at).toLocaleString('ja-JP')}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {(!dashboardData?.recent_messages || dashboardData.recent_messages.length === 0) && (
                    <p className="text-center text-gray-500 py-8">メッセージがありません</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;