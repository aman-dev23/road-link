import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, Circle } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { NearbyTraveller, SOSRequestItem } from '../api/client';

interface MapProps {
  userLat: number;
  userLon: number;
  hasLocation: boolean;
  accuracy?: number | null;
  nearbyTravellers: NearbyTraveller[];
  activeSOSRequests: SOSRequestItem[];
  onSelectSOS?: (sos: SOSRequestItem) => void;
  onSelectTraveller?: (traveller: NearbyTraveller) => void;
}

// Custom icons using Leaflet.divIcon for perfect rendering without asset loading errors
const userIcon = L.divIcon({
  className: 'custom-map-marker',
  html: `<div class="user-beacon"><div class="user-pulse"></div><div class="user-dot"></div></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const travellerIcon = (vehicleType: string) => {
  let symbol = '🚗';
  if (vehicleType === 'BIKE') symbol = '🏍️';
  if (vehicleType === 'TRUCK') symbol = '🚛';
  if (vehicleType === 'MECHANIC') symbol = '🔧';
  if (vehicleType === 'SOLO_WALKER') symbol = '🚶';

  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div class="traveller-marker"><span class="marker-symbol">${symbol}</span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

const sosIcon = (urgency: string) => {
  const isCritical = urgency === 'CRITICAL';
  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div class="sos-beacon ${isCritical ? 'critical' : ''}">
      <div class="sos-pulse"></div>
      <span class="sos-icon">🚨</span>
    </div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
  });
};

// Recenter component
function MapCenterController({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true });
  }, [lat, lon, map]);
  return null;
}

export const RoadLinkMap: React.FC<MapProps> = ({
  userLat,
  userLon,
  hasLocation,
  accuracy,
  nearbyTravellers,
  activeSOSRequests,
  onSelectSOS,
  onSelectTraveller,
}) => {
  return (
    <div className="map-wrapper">
      <MapContainer
        center={[userLat, userLon]}
        zoom={13}
        scrollWheelZoom={true}
        className="leaflet-container-custom"
      >
        <MapCenterController lat={userLat} lon={userLon} />

        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {hasLocation && (
          <>
            <Marker position={[userLat, userLon]} icon={userIcon}>
              <Popup>
                <div className="popup-card">
                  <h4>📍 You are here</h4>
                  <p>Lat: {userLat.toFixed(5)}, Lon: {userLon.toFixed(5)}</p>
                  {accuracy && <small>Accuracy: ±{Math.round(accuracy)}m</small>}
                </div>
              </Popup>
            </Marker>

            {accuracy && accuracy < 5000 && (
              <Circle
                center={[userLat, userLon]}
                radius={accuracy}
                pathOptions={{ fillColor: '#38bdf8', fillOpacity: 0.15, color: '#0284c7', weight: 1 }}
              />
            )}
          </>
        )}

        {/* Active Emergency SOS markers */}
        {activeSOSRequests.map((sos) => (
          <Marker
            key={sos.id}
            position={[sos.latitude, sos.longitude]}
            icon={sosIcon(sos.urgency)}
          >
            <Popup>
              <div className="popup-card sos-popup">
                <div className="popup-badge emergency">{sos.urgency} EMERGENCY</div>
                <h4>{sos.category.replace('_', ' ')}</h4>
                <p className="sos-desc">{sos.description || 'Assistance requested immediately'}</p>
                <div className="popup-meta">
                  <span>From: {sos.requester_name}</span>
                  {sos.distance_m && <span>• {Math.round(sos.distance_m / 1000 * 10) / 10} km away</span>}
                </div>
                {onSelectSOS && (
                  <button
                    className="popup-btn danger"
                    onClick={() => onSelectSOS(sos)}
                  >
                    View Emergency Details
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Nearby Travellers */}
        {nearbyTravellers.map((traveller) => (
          <Marker
            key={traveller.user_id}
            position={[traveller.latitude, traveller.longitude]}
            icon={travellerIcon(traveller.vehicle_type)}
          >
            <Popup>
              <div className="popup-card">
                <div className="popup-header">
                  <h4>{traveller.display_name}</h4>
                  <span className="badge-pill">{traveller.vehicle_type}</span>
                </div>
                <p className="dist-text">📍 {Math.round(traveller.distance_m / 1000 * 10) / 10} km away</p>
                {traveller.skills.length > 0 && (
                  <div className="skills-tags">
                    {traveller.skills.map((s) => (
                      <span key={s} className="skill-tag">{s.replace('_', ' ')}</span>
                    ))}
                  </div>
                )}
                {onSelectTraveller && (
                  <button
                    className="popup-btn"
                    onClick={() => onSelectTraveller(traveller)}
                  >
                    Contact Traveller
                  </button>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};
