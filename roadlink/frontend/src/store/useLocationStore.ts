import { create } from 'zustand';
import { api } from '../api/client';

interface LocationState {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  speed: number | null;
  heading: number | null;
  hasLocation: boolean;
  locationSource: 'gps' | 'manual' | null;
  gpsPermission: 'prompt' | 'granted' | 'denied';
  isTracking: boolean;
  error: string | null;
  watchId: number | null;
  startTracking: () => void;
  stopTracking: () => void;
  setLocationManual: (lat: number, lon: number) => Promise<void>;
  syncWithBackend: (lat: number, lon: number, acc?: number | null) => Promise<boolean>;
}

// Used only to center the map until the browser reports a real position.
const DEFAULT_LAT = 28.6139;
const DEFAULT_LON = 77.2090;

export const useLocationStore = create<LocationState>((set, get) => ({
  latitude: DEFAULT_LAT,
  longitude: DEFAULT_LON,
  accuracy: null,
  speed: null,
  heading: null,
  hasLocation: false,
  locationSource: null,
  gpsPermission: 'prompt',
  isTracking: false,
  error: null,
  watchId: null,

  syncWithBackend: async (lat: number, lon: number, acc?: number | null) => {
    try {
      await api.post('/api/locations/update', {
        latitude: lat,
        longitude: lon,
        accuracy_m: acc || null,
      });
      set({ error: null });
      return true;
    } catch {
      set({ error: 'Unable to sync your location. Check your connection and try again.' });
      return false;
    }
  },

  setLocationManual: async (lat: number, lon: number) => {
    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      set({ error: 'Latitude must be between -90 and 90.' });
      return;
    }
    if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
      set({ error: 'Longitude must be between -180 and 180.' });
      return;
    }
    if (!(await get().syncWithBackend(lat, lon))) return;
    get().stopTracking();
    set({
      latitude: lat,
      longitude: lon,
      accuracy: null,
      speed: null,
      heading: null,
      hasLocation: true,
      locationSource: 'manual',
    });
  },

  startTracking: () => {
    get().stopTracking();
    if (!navigator.geolocation) {
      set({ error: 'Geolocation is not supported by your browser', gpsPermission: 'denied' });
      return;
    }

    set({ isTracking: true });

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy, speed, heading } = pos.coords;
        set({
          latitude,
          longitude,
          accuracy,
          speed,
          heading,
          hasLocation: true,
          locationSource: 'gps',
          gpsPermission: 'granted',
          error: null,
        });
        get().syncWithBackend(latitude, longitude, accuracy);
      },
      (err) => {
        const denied = err.code === err.PERMISSION_DENIED;
        const msg = denied
          ? 'Location permission was denied. Allow GPS to find nearby travellers or send an SOS.'
          : err.code === err.TIMEOUT
            ? 'GPS request timed out. Try again or check your device location settings.'
            : 'Unable to determine your location. Check your device location settings.';
        set({
          error: msg,
          gpsPermission: denied ? 'denied' : 'prompt',
          isTracking: false,
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );

    // Watch position
    const id = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude, accuracy, speed, heading } = pos.coords;
        set({
          latitude,
          longitude,
          accuracy,
          speed,
          heading,
          hasLocation: true,
          locationSource: 'gps',
          gpsPermission: 'granted',
        });
        // Throttle backend sync
        get().syncWithBackend(latitude, longitude, accuracy);
      },
      (err) => {
        const denied = err.code === err.PERMISSION_DENIED;
        set({
          error: denied
            ? 'Location permission was denied. Allow GPS to find nearby travellers or send an SOS.'
            : 'Unable to update your GPS position. Check your device location settings.',
          gpsPermission: denied ? 'denied' : 'prompt',
        });
      },
      { enableHighAccuracy: true, maximumAge: 10000 }
    );

    set({ watchId: id });
  },

  stopTracking: () => {
    const { watchId } = get();
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
    }
    set({ isTracking: false, watchId: null });
  },
}));
