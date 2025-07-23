// Task List Component

import React, { useState } from 'react';
import { CheckSquare, Clock, User, AlertCircle, ChevronRight } from 'lucide-react';
import { Task } from '../types';
import { formatRelativeTime, getStatusColor, getPriorityColor, getAgentDisplayName } from '../services/api';

interface TaskListProps {
  tasks: Task[];
  showPagination?: boolean;
  onTaskClick?: (task: Task) => void;
}

const TaskList: React.FC<TaskListProps> = ({ 
  tasks, 
  showPagination = true, 
  onTaskClick 
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  
  const tasksPerPage = 10;

  // Filter tasks
  const filteredTasks = tasks.filter(task => {
    const statusMatch = statusFilter === 'all' || task.status === statusFilter;
    const priorityMatch = priorityFilter === 'all' || task.priority === priorityFilter;
    return statusMatch && priorityMatch;
  });

  // Paginate tasks
  const totalPages = Math.ceil(filteredTasks.length / tasksPerPage);
  const startIndex = (currentPage - 1) * tasksPerPage;
  const paginatedTasks = showPagination 
    ? filteredTasks.slice(startIndex, startIndex + tasksPerPage)
    : filteredTasks.slice(0, 10); // Show only first 10 if pagination is disabled

  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      pending: '待機中',
      in_progress: '進行中',
      completed: '完了',
      failed: '失敗',
      cancelled: 'キャンセル'
    };
    return statusMap[status] || status;
  };

  const getPriorityText = (priority: string): string => {
    const priorityMap: Record<string, string> = {
      low: '低',
      medium: '中',
      high: '高',
      critical: '緊急'
    };
    return priorityMap[priority] || priority;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckSquare className="h-4 w-4 text-emerald-500" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-amber-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  if (tasks.length === 0) {
    return (
      <div className="card p-8 text-center">
        <CheckSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <p className="text-gray-500">タスクがありません</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      {showPagination && (
        <div className="card p-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">ステータス:</label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-hive-primary focus:border-transparent"
              >
                <option value="all">すべて</option>
                <option value="pending">待機中</option>
                <option value="in_progress">進行中</option>
                <option value="completed">完了</option>
                <option value="failed">失敗</option>
                <option value="cancelled">キャンセル</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">優先度:</label>
              <select
                value={priorityFilter}
                onChange={(e) => {
                  setPriorityFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-hive-primary focus:border-transparent"
              >
                <option value="all">すべて</option>
                <option value="critical">緊急</option>
                <option value="high">高</option>
                <option value="medium">中</option>
                <option value="low">低</option>
              </select>
            </div>

            <div className="text-sm text-gray-500 flex items-center">
              {filteredTasks.length} 件中 {startIndex + 1}-{Math.min(startIndex + tasksPerPage, filteredTasks.length)} 件を表示
            </div>
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="card">
        <div className="divide-y divide-gray-200">
          {paginatedTasks.map((task) => (
            <div
              key={task.task_id}
              className={`p-4 hover:bg-gray-50 transition-colors ${
                onTaskClick ? 'cursor-pointer' : ''
              }`}
              onClick={() => onTaskClick?.(task)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  {/* Status Icon */}
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(task.status)}
                  </div>

                  {/* Task Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {task.title}
                      </h3>
                      <span className={`badge ${getPriorityColor(task.priority)}`}>
                        {getPriorityText(task.priority)}
                      </span>
                      <span className={`badge ${getStatusColor(task.status).includes('emerald') ? 'badge-success' : 
                                               getStatusColor(task.status).includes('amber') ? 'badge-warning' :
                                               getStatusColor(task.status).includes('red') ? 'badge-danger' : 'badge-gray'}`}>
                        {getStatusText(task.status)}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600 line-clamp-2 mb-2">
                      {task.description}
                    </p>

                    <div className="flex items-center space-x-4 text-xs text-gray-500">
                      {/* Assigned To */}
                      {task.assigned_to && (
                        <div className="flex items-center">
                          <User className="h-3 w-3 mr-1" />
                          {getAgentDisplayName(task.assigned_to)}
                        </div>
                      )}

                      {/* Created Date */}
                      <div className="flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {formatRelativeTime(task.created_at)}
                      </div>

                      {/* Estimated Hours */}
                      {task.estimated_hours && (
                        <div>
                          見積: {task.estimated_hours}h
                        </div>
                      )}

                      {/* Actual Hours (if completed) */}
                      {task.actual_hours && task.status === 'completed' && (
                        <div>
                          実績: {task.actual_hours}h
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Action Arrow */}
                {onTaskClick && (
                  <div className="flex-shrink-0 ml-4">
                    <ChevronRight className="h-4 w-4 text-gray-400" />
                  </div>
                )}
              </div>

              {/* Progress Bar (for in-progress tasks) */}
              {task.status === 'in_progress' && task.estimated_hours && task.actual_hours && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>進捗</span>
                    <span>
                      {Math.round((task.actual_hours / task.estimated_hours) * 100)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-hive-primary h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${Math.min((task.actual_hours / task.estimated_hours) * 100, 100)}%`
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Empty State */}
        {paginatedTasks.length === 0 && (
          <div className="p-8 text-center">
            <CheckSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">
              {statusFilter !== 'all' || priorityFilter !== 'all' 
                ? 'フィルター条件に一致するタスクがありません' 
                : 'タスクがありません'
              }
            </p>
          </div>
        )}
      </div>

      {/* Pagination */}
      {showPagination && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-700">
            {filteredTasks.length} 件中 {startIndex + 1}-{Math.min(startIndex + tasksPerPage, filteredTasks.length)} 件を表示
          </div>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              前へ
            </button>
            
            <div className="flex items-center space-x-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = i + 1;
                const isActive = pageNum === currentPage;
                
                return (
                  <button
                    key={pageNum}
                    onClick={() => setCurrentPage(pageNum)}
                    className={`px-3 py-1 text-sm rounded-md ${
                      isActive 
                        ? 'bg-hive-primary text-white' 
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
              
              {totalPages > 5 && (
                <>
                  <span className="text-gray-500">...</span>
                  <button
                    onClick={() => setCurrentPage(totalPages)}
                    className={`px-3 py-1 text-sm rounded-md ${
                      currentPage === totalPages 
                        ? 'bg-hive-primary text-white' 
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {totalPages}
                  </button>
                </>
              )}
            </div>
            
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              次へ
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskList;