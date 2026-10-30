import { useCallback, useEffect, useState, useTransition } from 'react';
import type { FormEvent } from 'react';
import { api } from './api/client';
import type { NearbyTraveller, SOSRequestItem } from './api/client';
import { RoadLinkMap } from './components/Map';
import { SOSModal } from './components/SOSModal';
import { ActiveSOSView } from './components/ActiveSOSView';
import { AuthModal } from './components/AuthModal';
import { ProfileModal } from './components/ProfileModal';
import { useAuthStore } from './store/useAuthStore';
import { useLocationStore } from './store/useLocationStore';
import { useSocketStore } from './store/useSocketStore';

type ActiveTab = 'map' | 'feed' | 'travellers';

export function App() {
  const { isAuthenticated, isLoading, fetchProfile } = useAuthStore();
  const {
    latitude,
    longitude,
    accuracy,
    hasLocation,
    locationSource,
    gpsPermission,
    error: locationError,
    startTracking,
    setLocationManual,
  } = useLocationStore();
  const { isConnected, notifications, connect, disconnect, dismissNotification } = useSocketStore();

  const [activeTab, setActiveTab] = useState<ActiveTab>('map');
  const [nearbyTravellers, setNearbyTravellers] = useState<NearbyTraveller[]>([]);
  const [sosFeed, setSosFeed] = useState<SOSRequestItem[]>([]);
  const [activeSOSList, setActiveSOSList] = useState<SOSRequestItem[]>([]);
  const [dataError, setDataError] = useState<string | null>(null);
  const [selectedSOS, setSelectedSOS] = useState<SOSRequestItem | null>(null);

  const [isSOSModalOpen, setIsSOSModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isManualLocationOpen, setIsManualLocationOpen] = useState(false);
  const [isSavingLocation, setIsSavingLocation] = useState(false);
  const [manualLatitude, setManualLatitude] = useState('');
  const [manualLongitude, setManualLongitude] = useState('');
  const [, startTransition] = useTransition();

  // Initialize Auth & Location tracking on mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchProfile();
      connect();
    } else {
      disconnect();
    }
    startTracking();
  }, [isAuthenticated, fetchProfile, connect, disconnect, startTracking]);

  // Fetch nearby travellers & SOS feed periodically
  const refreshData = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const [travellersRes, feedRes, activeRes] = await Promise.all([
        api.get('/api/locations/nearby?radius_m=35000'),
        api.get('/api/sos/feed'),
        api.get('/api/sos/active'),
      ]);
      startTransition(() => {
        setNearbyTravellers(travellersRes.data);
        setSosFeed(feedRes.data);
        setActiveSOSList(activeRes.data);
      });
      setDataError(null);
    } catch {
      setDataError('Unable to refresh nearby help. Check your connection and try again.');
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;

    const initialFetch = window.setTimeout(refreshData, 0);
    const interval = window.setInterval(refreshData, 10000);
    return () => {
      window.clearTimeout(initialFetch);
      window.clearInterval(interval);
    };
  }, [isAuthenticated, refreshData]);

  const handleOpenActiveSOS = (sos: SOSRequestItem) => {
    setSelectedSOS(sos);
  };

  const handleSOSCreated = (newSOS: SOSRequestItem) => {
    setActiveSOSList((prev) => [newSOS, ...prev]);
    setSelectedSOS(newSOS);
    refreshData();
  };

  const handleSOSUpdated = useCallback((updated: SOSRequestItem) => {
    setActiveSOSList((prev) =>
      prev.map((s) => (s.id === updated.id ? updated : s)).filter((s) => s.status !== 'RESOLVED' && s.status !== 'CANCELLED')
    );
    setSosFeed((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    refreshData();
  }, [refreshData]);

  const myOngoingEmergency = activeSOSList.find(
    (s) => s.status === 'OPEN' || s.status === 'ACCEPTED'
  );

  const saveManualLocation = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const lat = Number(manualLatitude);
    const lon = Number(manualLongitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    setIsSavingLocation(true);
    try {
      await setLocationManual(lat, lon);
      const location = useLocationStore.getState();
      if (location.hasLocation && location.locationSource === 'manual') {
        setIsManualLocationOpen(false);
        refreshData();
      }
    } finally {
      setIsSavingLocation(false);
    }
  };

  return (
    <div className="app-shell">
      {/* Top Navbar */}
      <header className="top-navbar">
        <div className="brand-section">
          <div className="brand-logo">
            <span>🛣️</span> RoadLink
          </div>
          <div
            className={`connection-dot ${isConnected ? 'online' : ''}`}
            title={isConnected ? 'Live WebSocket Connected' : 'Offline / Reconnecting'}
          />
        </div>

        <div className="nav-actions">
          <a href="tel:112" className="btn-emergency-112">
            <span>🚨</span> CALL 112
          </a>

          {isAuthenticated ? (
            <button
              className="btn-icon"
              title="Profile & Settings"
              onClick={() => setIsProfileModalOpen(true)}
            >
              👤
            </button>
          ) : (
            <button
              className="btn-primary"
              onClick={() => setIsAuthModalOpen(true)}
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Floating Alert Toasts */}
      {notifications.length > 0 && (
        <div className="toast-container">
          {notifications.map((n) => (
            <div key={n.id} className={`toast-item ${n.type.toLowerCase()}`}>
              <div className="toast-content">
                <strong>{n.title}</strong>
                <p>{n.message}</p>
              </div>
              <button
                className="toast-close"
                onClick={() => dismissNotification(n.id)}
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Active Ongoing Emergency Banner */}
      {myOngoingEmergency && (
        <div
          className="alert-banner error"
          style={{ cursor: 'pointer', margin: '4px 12px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          onClick={() => handleOpenActiveSOS(myOngoingEmergency)}
        >
          <div>
            <strong>🚨 Ongoing Emergency ({myOngoingEmergency.status})</strong>
            <p style={{ fontSize: '0.8rem' }}>
              {myOngoingEmergency.category.replace('_', ' ')} • Tap to view live status & chat
            </p>
          </div>
          <button className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Open Sheet
          </button>
        </div>
      )}

      {/* GPS Permission Warning Banner */}
      {locationError && (
        <div role="alert" className="alert-banner error" style={{ margin: '4px 12px 0', fontSize: '0.8rem' }}>
          ⚠️ {locationError}
          {gpsPermission === 'denied' && ' Call 112 if you need immediate emergency help.'}
        </div>
      )}
      {dataError && (
        <div role="alert" className="alert-banner error" style={{ margin: '4px 12px 0', fontSize: '0.8rem' }}>
          ⚠️ {dataError}
        </div>
      )}

      {/* Main Content Area */}
      <main className="app-content">
        {activeTab === 'map' && (
          <div className="map-view-container">
            <RoadLinkMap
              userLat={latitude}
              userLon={longitude}
              hasLocation={hasLocation}
              accuracy={accuracy}
              nearbyTravellers={nearbyTravellers}
              activeSOSRequests={sosFeed}
              onSelectSOS={handleOpenActiveSOS}
              onSelectTraveller={(t) => {
                alert(`Traveller: ${t.display_name}\nVehicle: ${t.vehicle_type}\nDistance: ${Math.round(t.distance_m / 1000 * 10) / 10} km\nSkills: ${t.skills.join(', ') || 'None listed'}`);
              }}
            />

            {/* Floating Action Overlay on top of Map */}
            <div className="floating-overlay-card">
              {isAuthenticated && (
                <div className="manual-location-panel">
                  {isManualLocationOpen ? (
                    <form onSubmit={saveManualLocation}>
                      <strong>Set your location manually</strong>
                      <p>Use coordinates you trust. Your location is shared with nearby RoadLink users.</p>
                      <div className="manual-location-fields">
                        <label>
                          Latitude
                          <input
                            type="number"
                            min="-90"
                            max="90"
                            step="any"
                            required
                            value={manualLatitude}
                            onChange={(event) => setManualLatitude(event.target.value)}
                          />
                        </label>
                        <label>
                          Longitude
                          <input
                            type="number"
                            min="-180"
                            max="180"
                            step="any"
                            required
                            value={manualLongitude}
                            onChange={(event) => setManualLongitude(event.target.value)}
                          />
                        </label>
                      </div>
                      <div className="manual-location-actions">
                        <button className="btn-primary" type="submit" disabled={isSavingLocation}>
                          {isSavingLocation ? 'Saving…' : 'Save location'}
                        </button>
                        <button className="link-btn" type="button" onClick={() => setIsManualLocationOpen(false)}>
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="manual-location-actions">
                      <span>
                        {locationSource === 'manual' ? 'Manual location · GPS tracking paused' : 'GPS unavailable?'}
                      </span>
                      <button className="link-btn" onClick={() => setIsManualLocationOpen(true)}>
                        {locationSource === 'manual' ? 'Change location' : 'Set location manually'}
                      </button>
                      {locationSource === 'manual' && (
                        <button className="link-btn" onClick={startTracking}>Use GPS</button>
                      )}
                    </div>
                  )}
                </div>
              )}
              <button
                className="sos-trigger-fab"
                disabled={isAuthenticated && !hasLocation}
                title={
                  isAuthenticated && !hasLocation
                    ? 'Enable GPS to send an SOS. Call 112 for immediate emergency help.'
                    : undefined
                }
                onClick={() => {
                  if (!isAuthenticated) {
                    setIsAuthModalOpen(true);
                  } else if (hasLocation) {
                    setIsSOSModalOpen(true);
                  }
                }}
              >
                <div className="sos-pulse-ring"></div>
                <span>
                  {isAuthenticated && !hasLocation
                    ? '📍 ENABLE LOCATION TO SEND SOS'
                    : '🚨 BROADCAST EMERGENCY SOS'}
                </span>
              </button>

              <div className="radar-quick-bar">
                <div className="radar-stat-item">
                  <span>Radar:</span>
                  <strong>{nearbyTravellers.length} travellers</strong>
                </div>
                <div className="radar-stat-item">
                  <span>Emergencies:</span>
                  <strong style={{ color: sosFeed.length > 0 ? '#ef4444' : '#10b981' }}>
                    {sosFeed.length} active
                  </strong>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'feed' && (
          <div className="list-view-container">
            <div className="list-section-title">
              <span>🚨 Emergency SOS Broadcasts</span>
              <button className="link-btn" onClick={refreshData}>Refresh</button>
            </div>

            {sosFeed.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                <p style={{ fontSize: '2rem', marginBottom: '8px' }}>🛡️</p>
                <h4>No Active Emergencies Nearby</h4>
                <p style={{ fontSize: '0.85rem' }}>The roads around you are currently all clear. If you face trouble, use the SOS button.</p>
              </div>
            ) : (
              sosFeed.map((sos) => (
                <div
                  key={sos.id}
                  className="traveller-card-item"
                  style={{ borderLeft: '4px solid #dc2626', cursor: 'pointer' }}
                  onClick={() => handleOpenActiveSOS(sos)}
                >
                  <div className="traveller-card-main">
                    <h4>
                      🚨 {sos.category.replace('_', ' ')}
                      <span className={`status-pill ${sos.status.toLowerCase()}`}>{sos.status}</span>
                    </h4>
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: '4px 0' }}>
                      {sos.description || 'Assistance requested'}
                    </p>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      From: {sos.requester_name} • {sos.distance_m ? `${Math.round(sos.distance_m / 1000 * 10) / 10} km away` : 'Nearby'}
                    </div>
                  </div>
                  <button className="btn-primary" style={{ padding: '8px 14px', fontSize: '0.8rem' }}>
                    Help
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'travellers' && (
          <div className="list-view-container">
            <div className="list-section-title">
              <span>👥 Nearby Motorists & Travellers</span>
              <button className="link-btn" onClick={refreshData}>Refresh</button>
            </div>

            {nearbyTravellers.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 20px', color: '#94a3b8' }}>
                <p style={{ fontSize: '2rem', marginBottom: '8px' }}>📡</p>
                <h4>Searching Radar...</h4>
                <p style={{ fontSize: '0.85rem' }}>No other visible travellers found within 35 km right now. As more users join or drive near, they will appear here automatically.</p>
              </div>
            ) : (
              nearbyTravellers.map((t) => (
                <div key={t.user_id} className="traveller-card-item">
                  <div className="traveller-card-main">
                    <h4>
                      {t.display_name}
                      <span className="badge-pill">{t.vehicle_type}</span>
                    </h4>
                    <p style={{ fontSize: '0.8rem', color: '#38bdf8' }}>
                      📍 {Math.round(t.distance_m / 1000 * 10) / 10} km away
                    </p>
                    {t.vehicle_description && (
                      <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        Vehicle: {t.vehicle_description}
                      </p>
                    )}
                    {t.skills.length > 0 && (
                      <div className="skills-tags">
                        {t.skills.map((s) => (
                          <span key={s} className="skill-tag">✓ {s.replace('_', ' ')}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </main>

      {/* Bottom Navigation */}
      <nav className="bottom-nav">
        <button
          className={`nav-tab-btn ${activeTab === 'map' ? 'active' : ''}`}
          onClick={() => setActiveTab('map')}
        >
          <span className="nav-tab-icon">🗺️</span>
          <span>Radar Map</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'feed' ? 'active' : ''}`}
          onClick={() => setActiveTab('feed')}
        >
          <span className="nav-tab-icon">🚨</span>
          <span>SOS Feed ({sosFeed.length})</span>
        </button>

        <button
          className={`nav-tab-btn ${activeTab === 'travellers' ? 'active' : ''}`}
          onClick={() => setActiveTab('travellers')}
        >
          <span className="nav-tab-icon">👥</span>
          <span>Travellers ({nearbyTravellers.length})</span>
        </button>

        <button
          className="nav-tab-btn"
          onClick={() => {
            if (isAuthenticated) {
              setIsProfileModalOpen(true);
            } else {
              setIsAuthModalOpen(true);
            }
          }}
        >
          <span className="nav-tab-icon">👤</span>
          <span>{isAuthenticated ? 'Profile' : 'Sign In'}</span>
        </button>
      </nav>

      {/* Modals */}
      <SOSModal
        isOpen={isSOSModalOpen}
        onClose={() => setIsSOSModalOpen(false)}
        userLat={latitude}
        userLon={longitude}
        onSOSCreated={handleSOSCreated}
      />

      {selectedSOS && (
        <ActiveSOSView
          sos={selectedSOS}
          onClose={() => setSelectedSOS(null)}
          onSOSUpdated={handleSOSUpdated}
        />
      )}

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      {isProfileModalOpen && !isLoading && (
        <ProfileModal
          isOpen
          onClose={() => setIsProfileModalOpen(false)}
        />
      )}
    </div>
  );
}

export default App;
