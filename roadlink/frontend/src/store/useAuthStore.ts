import { create } from 'zustand';
import { api } from '../api/client';
import type { Profile, User } from '../api/client';

interface AuthState {
  user: User | null;
  profile: Profile | null;
  skills: string[];
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken: string, user: User) => Promise<void>;
  logout: () => void;
  fetchProfile: () => Promise<void>;
  updateProfile: (data: Partial<Profile>) => Promise<void>;
  updateSkills: (skills: string[]) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  profile: null,
  skills: [],
  accessToken: localStorage.getItem('roadlink_access_token'),
  isAuthenticated: !!localStorage.getItem('roadlink_access_token'),
  isLoading: true,

  login: async (token, refreshToken, user) => {
    localStorage.setItem('roadlink_access_token', token);
    localStorage.setItem('roadlink_refresh_token', refreshToken);
    set({ accessToken: token, user, isAuthenticated: true });
    await get().fetchProfile();
  },

  logout: () => {
    const refreshToken = localStorage.getItem('roadlink_refresh_token');
    if (refreshToken) {
      api.post('/api/auth/logout', { refresh_token: refreshToken }).catch(() => { });
    }
    localStorage.removeItem('roadlink_access_token');
    localStorage.removeItem('roadlink_refresh_token');
    set({ user: null, profile: null, skills: [], accessToken: null, isAuthenticated: false });
  },

  fetchProfile: async () => {
    try {
      const resp = await api.get('/api/me');
      set({
        user: { id: resp.data.id, email: resp.data.email },
        profile: resp.data.profile,
        skills: resp.data.skills || [],
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      set({ isLoading: false });
    }
  },

  updateProfile: async (data: Partial<Profile>) => {
    const resp = await api.patch('/api/me/profile', data);
    set({ profile: resp.data });
  },

  updateSkills: async (skills: string[]) => {
    const resp = await api.put('/api/me/skills', { skills });
    set({ skills: resp.data });
  },
}));
