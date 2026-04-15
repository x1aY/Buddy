import { ref, onUnmounted } from 'vue';
import { ClientMessage, ServerMessage } from '@buddy/shared/src/types';
import { WEBSOCKET_RECONNECT_DELAY_MS, WEBSOCKET_PING_INTERVAL_MS } from '@buddy/shared/src/constants';

export function useWebSocketClient(token: string | null) {
  const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
  const isConnected = ref(false);
  const ws = ref<WebSocket | null>(null);
  const reconnectTimeout = ref<number | null>(null);
  const pingInterval = ref<number | null>(null);
  const messageHandlers = ref<Array<(message: ServerMessage) => void>>([]);

  function connect(): WebSocket {
    const url = new URL(wsUrl);
    if (token) {
      url.searchParams.set('token', token);
    }
    const socket = new WebSocket(url.toString());

    socket.onopen = () => {
      console.log('WebSocket connected');
      isConnected.value = true;
      startPing();
    };

    socket.onclose = () => {
      isConnected.value = false;
      stopPing();
      // Try to reconnect
      if (reconnectTimeout.value) {
        clearTimeout(reconnectTimeout.value);
      }
      reconnectTimeout.value = window.setTimeout(() => {
        console.log('Reconnecting...');
        connect();
      }, WEBSOCKET_RECONNECT_DELAY_MS);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as ServerMessage;
        // Invoke all registered handlers
        messageHandlers.value.forEach(handler => handler(message));
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    ws.value = socket;
    return socket;
  }

  function send(message: ClientMessage): void {
    if (ws.value && isConnected.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, message not sent', message);
    }
  }

  function onMessage(handler: (message: ServerMessage) => void): void {
    messageHandlers.value.push(handler);
    // If connection already exists, ensure our handler array is used
    if (ws.value && messageHandlers.value.length === 1) {
      // First handler attached after connection - onmessage already set in connect
    }
  }

  function offMessage(handler: (message: ServerMessage) => void): void {
    const index = messageHandlers.value.indexOf(handler);
    if (index !== -1) {
      messageHandlers.value.splice(index, 1);
    }
  }

  function disconnect(): void {
    if (reconnectTimeout.value) {
      clearTimeout(reconnectTimeout.value);
    }
    stopPing();
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    isConnected.value = false;
  }

  function startPing(): void {
    stopPing();
    pingInterval.value = window.setInterval(() => {
      send({ type: 'ping' });
    }, WEBSOCKET_PING_INTERVAL_MS);
  }

  function stopPing(): void {
    if (pingInterval.value) {
      clearInterval(pingInterval.value);
      pingInterval.value = null;
    }
  }

  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnected,
    connect,
    send,
    onMessage,
    offMessage,
    disconnect
  };
}
