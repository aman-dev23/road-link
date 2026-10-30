/**
 * API client for RoadLink backend
 */
import axios from 'axios';

export interface User {
  id: string;
  email: string;
}

export interface Profile {
  user_id: string;
  display_name: string;
  avatar_key?: string | null;
  avatar_url?: string | null;
  vehicle_type: string;
  vehicle_description?: string | null;
  preferred_language: string;
  is_available: boolean;
  visibility: 'VISIBLE' | 'HIDDEN';
  receive_sos: boolean;
  default_radius_m: number;
  onboarding_completed: boolean;
}

export interface UserWithProfile {
  id: string;
  email: string;
  status: string;
  sos_restricted: boolean;
  profile: Profile | null;
  skills: string[];
}

export interface NearbyTraveller {
  user_id: string;
  display_name: string;
  avatar_url?: string | null;
  vehicle_type: string;
  vehicle_description?: string | null;
  skills: string[];
  latitude: number;
  longitude: number;
  distance_m: number;
  is_available: boolean;
  updated_at: string;
}

export interface SOSRequestItem {
  id: string;
  requester_id: string;
  requester_name: string;
  requester_vehicle?: string | null;
  responder_id?: string | null;
  responder_name?: string | null;
  responder_vehicle?: string | null;
  category: string;
  urgency: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description?: string | null;
  latitude: number;
  longitude: number;
  current_radius_m: number;
  status: 'OPEN' | 'ACCEPTED' | 'RESOLVED' | 'CANCELLED';
  distance_m?: number | null;
  accepted_at?: string | null;
  resolved_at?: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  sos_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  created_at: string;
}

export const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT access token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('roadlink_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh token on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('roadlink_refresh_token');
      if (refreshToken) {
        try {
          const resp = await axios.post('/api/auth/refresh', { refresh_token: refreshToken });
          localStorage.setItem('roadlink_access_token', resp.data.access_token);
          localStorage.setItem('roadlink_refresh_token', resp.data.refresh_token);
          originalRequest.headers.Authorization = `Bearer ${resp.data.access_token}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('roadlink_access_token');
          localStorage.removeItem('roadlink_refresh_token');
          window.location.reload();
        }
      }
    }
    return Promise.reject(error);
  }
);
