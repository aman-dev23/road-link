import React, { useState } from 'react';
import { api } from '../api/client';
import type { SOSRequestItem } from '../api/client';

interface SOSModalProps {
  isOpen: boolean;
  onClose: () => void;
  userLat: number;
  userLon: number;
  onSOSCreated: (sos: SOSRequestItem) => void;
}

const CATEGORIES = [
  { id: 'VEHICLE_BREAKDOWN', label: 'Vehicle Breakdown', icon: '🚗' },
  { id: 'FUEL_SHORTAGE', label: 'Fuel Shortage', icon: '⛽' },
  { id: 'MEDICAL_EMERGENCY', label: 'Medical Emergency', icon: '🚑' },
  { id: 'ACCIDENT', label: 'Accident', icon: '💥' },
  { id: 'FOOD_WATER', label: 'Food & Water', icon: '🍞' },
  { id: 'MECHANICAL_ASSISTANCE', label: 'Mechanical Help', icon: '🔧' },
  { id: 'NEED_DIRECTIONS', label: 'Need Directions', icon: '🗺️' },
  { id: 'OTHER', label: 'Other', icon: '❓' },
];

const URGENCIES = [
  { id: 'CRITICAL', label: 'Critical', desc: 'Immediate danger or medical risk', color: '#dc2626' },
  { id: 'HIGH', label: 'High', desc: 'Stranded or unsafe location', color: '#ea580c' },
  { id: 'MEDIUM', label: 'Medium', desc: 'Need assistance soon', color: '#eab308' },
  { id: 'LOW', label: 'Low', desc: 'Not immediately dangerous', color: '#10b981' },
];

export const SOSModal: React.FC<SOSModalProps> = ({
  isOpen,
  onClose,
  userLat,
  userLon,
  onSOSCreated,
}) => {
  const [category, setCategory] = useState('VEHICLE_BREAKDOWN');
  const [urgency, setUrgency] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('HIGH');
  const [description, setDescription] = useState('');
  const [radiusM, setRadiusM] = useState(15000);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const resp = await api.post('/api/sos', {
        category,
        urgency,
        description: description.trim() || null,
        latitude: userLat,
        longitude: userLon,
        initial_radius_m: radiusM,
      });
      onSOSCreated(resp.data);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || 'Failed to broadcast SOS. Please check connection.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle"></div>
        <div className="modal-header emergency">
          <div className="header-icon">🚨</div>
          <div>
            <h3>Emergency Assistance Request</h3>
            <p className="subtext">Broadcast your situation to eligible nearby travellers</p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {error && <div className="alert-banner error">{error}</div>}

        <form onSubmit={handleSubmit} className="sos-form">
          {/* Emergency Category */}
          <div className="form-group">
            <label className="section-label">Select Problem Category</label>
            <div className="category-grid">
              {CATEGORIES.map((cat) => (
                <button
                  type="button"
                  key={cat.id}
                  className={`category-chip ${category === cat.id ? 'active' : ''}`}
                  onClick={() => setCategory(cat.id)}
                >
                  <span className="cat-icon">{cat.icon}</span>
                  <span className="cat-label">{cat.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Urgency Level */}
          <div className="form-group">
            <label className="section-label">Urgency Level</label>
            <div className="urgency-grid">
              {URGENCIES.map((u) => (
                <button
                  type="button"
                  key={u.id}
                  className={`urgency-card ${urgency === u.id ? 'active' : ''}`}
                  onClick={() => setUrgency(u.id as any)}
                >
                  <div className="urgency-indicator" style={{ backgroundColor: u.color }}></div>
                  <div className="urgency-info">
                    <span className="urgency-title">{u.label}</span>
                    <small>{u.desc}</small>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Details */}
          <div className="form-group">
            <label className="section-label">Details / What do you need?</label>
            <textarea
              className="text-input"
              rows={3}
              placeholder="e.g. Need tyre change assistance or fuel for hatchback near mile marker 42"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={1000}
            />
          </div>

          {/* Broadcast Radius & GPS Coordinates */}
          <div className="form-group">
            <label className="section-label">Broadcast Search Radius</label>
            <div className="radius-selector">
              {[5000, 15000, 30000, 50000].map((r) => (
                <button
                  type="button"
                  key={r}
                  className={`radius-chip ${radiusM === r ? 'active' : ''}`}
                  onClick={() => setRadiusM(r)}
                >
                  {r / 1000} km
                </button>
              ))}
            </div>
            <div className="gps-preview">
              <span>📍 Broadcast Location:</span>
              <code>{userLat.toFixed(5)}, {userLon.toFixed(5)}</code>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="sos-action-bar">
            <a href="tel:112" className="btn-call-112">
              📞 Direct Call 112
            </a>
            <button
              type="submit"
              className="btn-trigger-sos"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Broadcasting Emergency...' : '🚨 BROADCAST SOS NOW'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
