import React, { useState } from 'react';
import { useAuthStore } from '../store/useAuthStore';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const VEHICLE_OPTIONS = [
  { value: 'CAR', label: '🚗 Car / SUV' },
  { value: 'BIKE', label: '🏍️ Motorcycle / Scooter' },
  { value: 'TRUCK', label: '🚛 Truck / Heavy Vehicle' },
  { value: 'MECHANIC', label: '🔧 Service / Mechanic Van' },
  { value: 'SOLO_WALKER', label: '🚶 On Foot / Bicycle' },
  { value: 'OTHER', label: '🚙 Other Vehicle' },
];

const SKILL_OPTIONS = [
  { value: 'MECHANIC', label: '🔧 Mechanic / Tool Kit' },
  { value: 'FIRST_AID', label: '🩹 First Aid Certified' },
  { value: 'TOWING', label: '🪢 Tow Rope / Cable' },
  { value: 'FUEL_SUPPLY', label: '⛽ Extra Fuel / Can' },
  { value: 'NAVIGATION_HELP', label: '🗺️ Local Route Guide' },
  { value: 'TRANSLATION', label: '🗣️ Local Language Help' },
];

export const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose }) => {
  const { profile, skills, updateProfile, updateSkills, logout } = useAuthStore();

  const [displayName, setDisplayName] = useState(profile?.display_name || '');
  const [vehicleType, setVehicleType] = useState(profile?.vehicle_type || 'CAR');
  const [vehicleDesc, setVehicleDesc] = useState(profile?.vehicle_description || '');
  const [selectedSkills, setSelectedSkills] = useState<string[]>(skills || []);
  const [visibility, setVisibility] = useState<'VISIBLE' | 'HIDDEN'>(profile?.visibility || 'VISIBLE');
  const [receiveSOS, setReceiveSOS] = useState(profile?.receive_sos ?? true);
  const [radiusM, setRadiusM] = useState(profile?.default_radius_m || 25000);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const toggleSkill = (val: string) => {
    setSelectedSkills((prev) =>
      prev.includes(val) ? prev.filter((s) => s !== val) : [...prev, val]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await updateProfile({
        display_name: displayName.trim(),
        vehicle_type: vehicleType,
        vehicle_description: vehicleDesc.trim() || null,
        visibility,
        receive_sos: receiveSOS,
        default_radius_m: radiusM,
      });
      await updateSkills(selectedSkills);
      setMsg('Profile preferences updated successfully.');
      setTimeout(() => onClose(), 1000);
    } catch {
      setMsg('Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-sheet profile-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle"></div>

        <div className="modal-header">
          <h3>Traveller Profile & Settings</h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {msg && <div className="alert-banner success">{msg}</div>}

        <form onSubmit={handleSave} className="profile-form">
          <div className="form-group">
            <label>Display Name</label>
            <input
              type="text"
              required
              minLength={2}
              maxLength={40}
              className="text-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Vehicle Type</label>
            <select
              className="select-input"
              value={vehicleType}
              onChange={(e) => setVehicleType(e.target.value)}
            >
              {VEHICLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Vehicle Description (Make, Model, Color)</label>
            <input
              type="text"
              maxLength={100}
              className="text-input"
              placeholder="e.g. Silver Swift, DL-04-AB-1234"
              value={vehicleDesc}
              onChange={(e) => setVehicleDesc(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Skills & Emergency Equipment you carry</label>
            <div className="skills-checklist">
              {SKILL_OPTIONS.map((s) => (
                <label key={s.value} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedSkills.includes(s.value)}
                    onChange={() => toggleSkill(s.value)}
                  />
                  <span>{s.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label>Default Radar Radius</label>
            <select
              className="select-input"
              value={radiusM}
              onChange={(e) => setRadiusM(Number(e.target.value))}
            >
              <option value={5000}>5 km</option>
              <option value={10000}>10 km</option>
              <option value={25000}>25 km</option>
              <option value={50000}>50 km</option>
              <option value={100000}>100 km</option>
            </select>
          </div>

          <div className="form-group">
            <label>Location Visibility & Privacy</label>
            <div className="radio-group">
              <label className="radio-item">
                <input
                  type="radio"
                  name="visibility"
                  value="VISIBLE"
                  checked={visibility === 'VISIBLE'}
                  onChange={() => setVisibility('VISIBLE')}
                />
                <div>
                  <strong>Visible on RoadLink Radar</strong>
                  <p>Other nearby verified motorists can see you and ask for/offer help.</p>
                </div>
              </label>

              <label className="radio-item">
                <input
                  type="radio"
                  name="visibility"
                  value="HIDDEN"
                  checked={visibility === 'HIDDEN'}
                  onChange={() => setVisibility('HIDDEN')}
                />
                <div>
                  <strong>Ghost Mode (Hidden)</strong>
                  <p>You can still see nearby emergencies, but your location is hidden from radar.</p>
                </div>
              </label>
            </div>
          </div>

          <div className="form-group">
            <label className="checkbox-item receive-sos-toggle">
              <input
                type="checkbox"
                checked={receiveSOS}
                onChange={(e) => setReceiveSOS(e.target.checked)}
              />
              <div>
                <strong>Receive Emergency SOS Notifications</strong>
                <p>Alert me when another traveller is stranded nearby</p>
              </div>
            </label>
          </div>

          <div className="form-actions-split">
            <button
              type="button"
              className="btn-danger-outline"
              onClick={() => { logout(); onClose(); }}
            >
              Sign Out
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
