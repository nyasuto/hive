// WebSocket hook for real-time communication

import { useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketMessage } from '../types';

interface UseWebSocketReturn {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: any) => void;
  reconnect: () => void;
  connectionError: string | null;
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    try {
      const wsUrl = process.env.NODE_ENV === 'production' 
        ? `wss://${window.location.host}/ws/`
        : 'ws://localhost:8000/ws/';

      console.log('🔗 Connecting to WebSocket:', wsUrl);
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
        
        // Send initial ping
        ws.current?.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('📨 WebSocket message:', message.type);
          setLastMessage(message);
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
        }
      };

      ws.current.onclose = (event) => {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt reconnection if not a normal closure
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setConnectionError('最大再接続試行回数に達しました');
        }
      };

      ws.current.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        setConnectionError('WebSocket接続エラーが発生しました');
      };

    } catch (error) {
      console.error('❌ Failed to create WebSocket connection:', error);
      setConnectionError('WebSocket接続の作成に失敗しました');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }
    
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        ws.current.send(JSON.stringify(message));
        console.log('📤 Sent WebSocket message:', message.type);
      } catch (error) {
        console.error('❌ Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('⚠️ WebSocket not connected, cannot send message');
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setConnectionError(null);
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Ping/keepalive mechanism
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      sendMessage({
        type: 'ping',
        timestamp: new Date().toISOString()
      });
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(interval);
  }, [isConnected, sendMessage]);

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect,
    connectionError
  };
};