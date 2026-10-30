import { create } from 'zustand';
import { api } from '../api/client';
import type { ChatMessage, SOSRequestItem } from '../api/client';

export interface SocketEventData {
  event_id?: string;
  sos?: SOSRequestItem;
  message?: ChatMessage;
  user_id?: string;
}

export interface AlertNotification {
  id: string;
  type: 'SOS_ALERT' | 'SOS_ACCEPTED' | 'SOS_RESOLVED' | 'SOS_CANCELLED' | 'CHAT_MESSAGE';
  title: string;
  message: string;
  data: any;
  timestamp: Date;
}

interface SocketState {
  isConnected: boolean;
  socket: WebSocket | null;
  notifications: AlertNotification[];
  connect: () => Promise<void>;
  disconnect: () => void;
  dismissNotification: (id: string) => void;
  onEvent?: (event: string, data: SocketEventData) => void;
  setOnEvent: (fn: (event: string, data: SocketEventData) => void) => void;
}

export const useSocketStore = create<SocketState>((set, get) => ({
  isConnected: false,
  socket: null,
  notifications: [],

  setOnEvent: (fn) => set({ onEvent: fn }),

  dismissNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  connect: async () => {
    if (get().socket || !localStorage.getItem('roadlink_access_token')) return;

    try {
      const resp = await api.post('/api/ws/ticket');
      const ticket = resp.data.ticket;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws?ticket=${ticket}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        set({ isConnected: true, socket: ws });
      };

      ws.onmessage = (e) => {
        try {
          const payload = JSON.parse(e.data);
          const { event, ...rest } = payload;

          let notif: AlertNotification | null = null;
          if (event === 'SOS_ALERT') {
            notif = {
              id: rest.event_id || Math.random().toString(),
              type: 'SOS_ALERT',
              title: `🚨 EMERGENCY: ${rest.sos?.category || 'ASSISTANCE'}`,
              message: `${rest.sos?.requester_name || 'A traveller'} needs help nearby (${rest.sos?.urgency || 'MEDIUM'} urgency)`,
              data: rest.sos,
              timestamp: new Date(),
            };
          } else if (event === 'SOS_ACCEPTED') {
            notif = {
              id: rest.event_id || Math.random().toString(),
              type: 'SOS_ACCEPTED',
              title: '✅ Help is on the way!',
              message: `${rest.sos?.responder_name || 'A responder'} accepted your SOS request`,
              data: rest.sos,
              timestamp: new Date(),
            };
          } else if (event === 'CHAT_MESSAGE') {
            notif = {
              id: rest.event_id || Math.random().toString(),
              type: 'CHAT_MESSAGE',
              title: `💬 ${rest.message?.sender_name || 'New message'}`,
              message: rest.message?.content || '',
              data: rest.message,
              timestamp: new Date(),
            };
          }

          if (notif) {
            set((state) => {
              if (state.notifications.some((item) => item.id === notif!.id)) {
                return state;
              }
              return {
                notifications: [notif!, ...state.notifications.slice(0, 4)],
              };
            });
          }

          if (get().onEvent) {
            get().onEvent!(event, rest);
          }
        } catch {}
      };

      ws.onclose = () => {
        set({ isConnected: false, socket: null });
        // Attempt reconnect in 5 seconds if authenticated
        setTimeout(() => {
          if (localStorage.getItem('roadlink_access_token')) {
            get().connect();
          }
        }, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // Re-try ticket in 10 seconds
      setTimeout(() => {
        if (localStorage.getItem('roadlink_access_token')) {
          get().connect();
        }
      }, 10000);
    }
  },

  disconnect: () => {
    const ws = get().socket;
    if (ws) {
      ws.close();
    }
    set({ isConnected: false, socket: null });
  },
}));
