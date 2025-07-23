// Instruction Form Component

import React, { useState, useEffect } from 'react';
import { Send, Loader2, BookOpen, Check, AlertTriangle } from 'lucide-react';
import { instructionsApi } from '../services/api';
import { InstructionRequest, InstructionTemplate, AgentType, Priority } from '../types';

interface InstructionFormProps {
  onInstructionSent?: () => void;
}

const InstructionForm: React.FC<InstructionFormProps> = ({ onInstructionSent }) => {
  const [formData, setFormData] = useState<InstructionRequest>({
    content: '',
    target_agent: 'developer' as AgentType,
    priority: 'medium' as Priority,
    create_task: true,
    subject: ''
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [templates, setTemplates] = useState<InstructionTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [showTemplates, setShowTemplates] = useState(false);

  // Load templates on component mount
  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const response = await instructionsApi.getTemplates();
      setTemplates(response.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setFormData(prev => ({
        ...prev,
        content: template.template,
        target_agent: template.target_agent as AgentType,
        priority: template.priority,
        subject: template.name
      }));
      setSelectedTemplate(templateId);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.content.trim()) {
      setErrorMessage('指示内容を入力してください');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const response = await instructionsApi.sendInstruction(formData);
      
      setSuccessMessage(
        `指示を送信しました${response.task_created ? '（タスクも作成されました）' : ''}`
      );
      
      // Reset form
      setFormData({
        content: '',
        target_agent: 'developer' as AgentType,
        priority: 'medium' as Priority,
        create_task: true,
        subject: ''
      });
      setSelectedTemplate('');
      
      // Notify parent component
      onInstructionSent?.();
      
      // Auto-hide success message
      setTimeout(() => {
        setSuccessMessage('');
      }, 5000);
      
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '指示の送信に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const agentOptions = [
    { value: 'queen', label: '👑 Queen Bee', description: 'タスク管理・調整' },
    { value: 'developer', label: '💻 Developer', description: 'コード実装・開発' },
    { value: 'qa', label: '🧪 QA', description: 'テスト・品質保証' },
    { value: 'analyst', label: '📊 Analyst', description: 'パフォーマンス分析' },
    { value: 'all', label: '🌐 全員', description: 'すべてのエージェント' }
  ];

  const priorityOptions = [
    { value: 'low', label: '低', color: 'text-green-600 bg-green-100' },
    { value: 'medium', label: '中', color: 'text-blue-600 bg-blue-100' },
    { value: 'high', label: '高', color: 'text-amber-600 bg-amber-100' },
    { value: 'critical', label: '緊急', color: 'text-red-600 bg-red-100' }
  ];

  return (
    <div className="card p-6">
      {/* Success Message */}
      {successMessage && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-md">
          <div className="flex items-center">
            <Check className="h-4 w-4 text-emerald-500 mr-2" />
            <p className="text-sm text-emerald-700">{successMessage}</p>
          </div>
        </div>
      )}

      {/* Error Message */}
      {errorMessage && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center">
            <AlertTriangle className="h-4 w-4 text-red-500 mr-2" />
            <p className="text-sm text-red-700">{errorMessage}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Template Selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              テンプレート
            </label>
            <button
              type="button"
              onClick={() => setShowTemplates(!showTemplates)}
              className="text-sm text-hive-primary hover:text-amber-600 flex items-center"
            >
              <BookOpen className="h-4 w-4 mr-1" />
              {showTemplates ? '閉じる' : 'テンプレート表示'}
            </button>
          </div>
          
          {showTemplates && (
            <div className="grid grid-cols-1 gap-2 p-3 bg-gray-50 rounded-md max-h-40 overflow-y-auto">
              {templates.map((template) => (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => handleTemplateSelect(template.id)}
                  className={`text-left p-2 rounded-md text-sm transition-colors ${
                    selectedTemplate === template.id
                      ? 'bg-hive-primary text-white'
                      : 'bg-white hover:bg-gray-100 text-gray-700'
                  }`}
                >
                  <div className="font-medium">{template.name}</div>
                  <div className="text-xs opacity-75 mt-1">
                    対象: {agentOptions.find(a => a.value === template.target_agent)?.label}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Subject */}
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
            件名 <span className="text-gray-400">(オプション)</span>
          </label>
          <input
            type="text"
            id="subject"
            value={formData.subject}
            onChange={(e) => setFormData(prev => ({ ...prev, subject: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-hive-primary focus:border-transparent"
            placeholder="指示の件名を入力..."
          />
        </div>

        {/* Target Agent */}
        <div>
          <label htmlFor="target_agent" className="block text-sm font-medium text-gray-700 mb-1">
            対象エージェント
          </label>
          <select
            id="target_agent"
            value={formData.target_agent}
            onChange={(e) => setFormData(prev => ({ ...prev, target_agent: e.target.value as AgentType }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-hive-primary focus:border-transparent"
          >
            {agentOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} - {option.description}
              </option>
            ))}
          </select>
        </div>

        {/* Priority */}
        <div>
          <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
            優先度
          </label>
          <div className="grid grid-cols-4 gap-2">
            {priorityOptions.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, priority: option.value as Priority }))}
                className={`p-2 rounded-md text-sm font-medium transition-colors ${
                  formData.priority === option.value
                    ? option.color
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div>
          <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-1">
            指示内容 *
          </label>
          <textarea
            id="content"
            rows={4}
            value={formData.content}
            onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-hive-primary focus:border-transparent"
            placeholder="エージェントへの指示を入力してください..."
            required
          />
          <div className="mt-1 text-xs text-gray-500">
            {formData.content.length}/2000文字
          </div>
        </div>

        {/* Create Task Option */}
        <div className="flex items-center">
          <input
            type="checkbox"
            id="create_task"
            checked={formData.create_task}
            onChange={(e) => setFormData(prev => ({ ...prev, create_task: e.target.checked }))}
            className="h-4 w-4 text-hive-primary focus:ring-hive-primary border-gray-300 rounded"
          />
          <label htmlFor="create_task" className="ml-2 text-sm text-gray-700">
            自動的にタスクを作成する
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting || !formData.content.trim()}
          className="w-full flex items-center justify-center btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              送信中...
            </>
          ) : (
            <>
              <Send className="h-4 w-4 mr-2" />
              指示を送信
            </>
          )}
        </button>
      </form>

      {/* Form Help */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-900 mb-2">使用方法</h4>
        <ul className="text-xs text-gray-600 space-y-1">
          <li>• 対象エージェントを選択して指示を送信できます</li>
          <li>• テンプレートを使用すると素早く指示を作成できます</li>
          <li>• 「全員」を選択すると全エージェントに指示が送信されます</li>
          <li>• タスク作成をオンにすると、自動的にタスクが生成されます</li>
        </ul>
      </div>
    </div>
  );
};

export default InstructionForm;