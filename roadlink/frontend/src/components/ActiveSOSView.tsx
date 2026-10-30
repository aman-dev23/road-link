import React, { useCallback, useEffect, useState, useRef } from 'react';
import { api } from '../api/client';
import type { ChatMessage, SOSRequestItem } from '../api/client';
import { useAuthStore } from '../store/useAuthStore';
import { useSocketStore } from '../store/useSocketStore';
import type { SocketEventData } from '../store/useSocketStore';

interface ActiveSOSViewProps {
  sos: SOSRequestItem;
  onClose: () => void;
  onSOSUpdated: (updated: SOSRequestItem) => void;
}

export const ActiveSOSView: React.FC<ActiveSOSViewProps> = ({
  sos,
  onClose,
  onSOSUpdated,
}) => {
  const { user } = useAuthStore();
  const setOnEvent = useSocketStore((state) => state.setOnEvent);
  const [currentSOS, setCurrentSOS] = useState<SOSRequestItem>(sos);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMsg, setNewMsg] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const isRequester = user?.id === currentSOS.requester_id;
  const isResponder = user?.id === currentSOS.responder_id;
  const isParticipant = isRequester || isResponder;
  const isAccepted = currentSOS.status === 'ACCEPTED';
  const isOpen = currentSOS.status === 'OPEN';

  // Load chat history if participant
  useEffect(() => {
    if (!isParticipant) return;
    let cancelled = false;

    api.get(`/api/sos/${currentSOS.id}/chat`).then((resp) => {
      if (cancelled) return;
      setMessages((previous) => {
        const merged = new Map<string, ChatMessage>(
          resp.data.map((message: ChatMessage) => [message.id, message])
        );
        previous.forEach((message) => merged.set(message.id, message));
        return [...merged.values()].sort(
          (left, right) =>
            new Date(left.created_at).getTime() - new Date(right.created_at).getTime()
        );
      });
      setActionError(null);
    }).catch(() => {
      if (!cancelled) {
        setActionError('Unable to load private chat. Check your connection and try again.');
      }
    });

    return () => {
      cancelled = true;
    };
  }, [currentSOS.id, isParticipant]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Listen to live WebSocket events
  const handleSocketEvent = useCallback((event: string, data: SocketEventData) => {
    const message = data.message;
    if (event === 'CHAT_MESSAGE' && message && message.sos_id === currentSOS.id) {
      setMessages((prev) =>
        prev.some((existing) => existing.id === message.id)
          ? prev
          : [...prev, message]
      );
    } else if (
      (event === 'SOS_ACCEPTED' || event === 'SOS_RESOLVED' || event === 'SOS_CANCELLED') &&
      data.sos?.id === currentSOS.id
    ) {
      setCurrentSOS(data.sos);
      onSOSUpdated(data.sos);
    }
  }, [currentSOS.id, onSOSUpdated]);

  useEffect(() => {
    setOnEvent(handleSocketEvent);
    return () => setOnEvent(() => {});
  }, [handleSocketEvent, setOnEvent]);

  const handleAccept = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      const resp = await api.post(`/api/sos/${currentSOS.id}/accept`);
      setCurrentSOS(resp.data);
      onSOSUpdated(resp.data);
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || 'Failed to accept SOS');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleResolve = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      const resp = await api.post(`/api/sos/${currentSOS.id}/resolve`, { notes: 'Resolved by participant' });
      setCurrentSOS(resp.data);
      onSOSUpdated(resp.data);
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || 'Failed to resolve emergency');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleCancel = async () => {
    setIsActionLoading(true);
    setActionError(null);
    try {
      const resp = await api.post(`/api/sos/${currentSOS.id}/cancel`, { reason: 'Cancelled by requester' });
      setCurrentSOS(resp.data);
      onSOSUpdated(resp.data);
    } catch (err: any) {
      setActionError(err.response?.data?.detail?.message || 'Failed to cancel SOS');
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMsg.trim() || isSending) return;
    setIsSending(true);
    try {
      const resp = await api.post(`/api/sos/${currentSOS.id}/chat`, { content: newMsg.trim() });
      setMessages((prev) => [...prev, resp.data]);
      setNewMsg('');
    } catch {
      setActionError('Message could not be sent. Check your connection and try again.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet active-sos-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle"></div>

        <div className="sos-view-header">
          <div className="sos-status-badge-row">
            <span className={`status-pill ${currentSOS.status.toLowerCase()}`}>
              {currentSOS.status}
            </span>
            <span className={`urgency-pill ${currentSOS.urgency.toLowerCase()}`}>
              {currentSOS.urgency} URGENCY
            </span>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {actionError && <div className="alert-banner error">{actionError}</div>}

        <div className="sos-view-content">
          <h3 className="sos-category-title">
            🚨 {currentSOS.category.replace('_', ' ')}
          </h3>
          <p className="sos-detail-desc">
            {currentSOS.description || 'Assistance requested.'}
          </p>

          <div className="sos-participants-grid">
            <div className="participant-card">
              <span className="p-role">Requester</span>
              <strong className="p-name">{currentSOS.requester_name}</strong>
              <small className="p-vehicle">{currentSOS.requester_vehicle || 'Vehicle'}</small>
            </div>
            <div className="participant-card">
              <span className="p-role">Responder</span>
              {currentSOS.responder_name ? (
                <>
                  <strong className="p-name">{currentSOS.responder_name}</strong>
                  <small className="p-vehicle">{currentSOS.responder_vehicle || 'Vehicle'}</small>
                </>
              ) : (
                <span className="waiting-text">Waiting for responder...</span>
              )}
            </div>
          </div>

          <div className="sos-location-strip">
            <span>📍 Coordinates: {currentSOS.latitude.toFixed(5)}, {currentSOS.longitude.toFixed(5)}</span>
            {currentSOS.distance_m && (
              <span>• ~{Math.round(currentSOS.distance_m / 1000 * 10) / 10} km from you</span>
            )}
          </div>

          {/* Action Bar for Acceptance / Resolution / Cancellation */}
          <div className="sos-controls-row">
            {isOpen && !isRequester && (
              <button
                className="btn-accept-sos"
                onClick={handleAccept}
                disabled={isActionLoading}
              >
                {isActionLoading ? 'Accepting...' : '🤝 ACCEPT & RESPOND TO SOS'}
              </button>
            )}

            {isAccepted && isParticipant && (
              <button
                className="btn-resolve-sos"
                onClick={handleResolve}
                disabled={isActionLoading}
              >
                {isActionLoading ? 'Resolving...' : '✅ Mark Emergency Resolved'}
              </button>
            )}

            {(isOpen || isAccepted) && isRequester && (
              <button
                className="btn-cancel-sos"
                onClick={handleCancel}
                disabled={isActionLoading}
              >
                {isActionLoading ? 'Cancelling...' : 'Cancel SOS Request'}
              </button>
            )}

            <a href="tel:112" className="btn-call-112 compact">
              📞 Call 112
            </a>
          </div>

          {/* Private Requester-Responder Live Chat */}
          {isParticipant && (
            <div className="sos-chat-section">
              <div className="chat-header">
                <h4>💬 Direct Communication</h4>
                <small>Secure connection between Requester and Responder</small>
              </div>

              <div className="chat-thread">
                {messages.length === 0 ? (
                  <div className="chat-empty">
                    No messages yet. Send a message to coordinate arrival or share status.
                  </div>
                ) : (
                  messages.map((m) => {
                    const isMe = m.sender_id === user?.id;
                    return (
                      <div key={m.id} className={`chat-bubble ${isMe ? 'outgoing' : 'incoming'}`}>
                        <div className="bubble-sender">{m.sender_name}</div>
                        <div className="bubble-text">{m.content}</div>
                        <div className="bubble-time">
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={chatBottomRef}></div>
              </div>

              {currentSOS.status !== 'RESOLVED' && currentSOS.status !== 'CANCELLED' && (
                <form onSubmit={handleSendMessage} className="chat-input-bar">
                  <input
                    type="text"
                    className="chat-text-input"
                    placeholder="Type a message (e.g. ETA, landmarks, tools)..."
                    value={newMsg}
                    onChange={(e) => setNewMsg(e.target.value)}
                    maxLength={1000}
                  />
                  <button type="submit" className="chat-send-btn" disabled={isSending || !newMsg.trim()}>
                    Send
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
