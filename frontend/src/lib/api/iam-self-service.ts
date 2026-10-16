/**
 * IAM Self-Service API
 */

import axios from 'axios';

// Use relative URLs to leverage Next.js rewrites

export interface Profile {
  id: string;
  username: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  locale?: string;
  timezone?: string;
  emailVerified: boolean;
}

export interface ProfileUpdate {
  firstName?: string;
  lastName?: string;
  locale?: string;
  timezone?: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface Session {
  id: string;
  username: string;
  userId: string;
  ipAddress?: string;
  start?: number;
  lastAccess?: number;
  clients: Record<string, any>;
}

export interface App {
  id: string;
  clientId: string;
  name: string;
  baseUrl?: string;
  description?: string;
}

export async function getProfile(_token?: string): Promise<Profile> {
  const response = await axios.get(`/api/v1/self/profile`, {
    withCredentials: true,
  });
  return response.data;
}

export async function updateProfile(
  data: ProfileUpdate,
  _token?: string
): Promise<Profile> {
  const response = await axios.put(`/api/v1/self/profile`, data, {
    withCredentials: true,
  });
  return response.data;
}

export async function changePassword(
  data: PasswordChange,
  _token?: string
): Promise<{ success: boolean; message: string }> {
  const response = await axios.post(
    `/api/v1/self/password/change`,
    data,
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function requestPasswordReset(
  _token?: string
): Promise<{ success: boolean; message: string; email_sent?: boolean }> {
  const response = await axios.post(
    `/api/v1/self/password/reset`,
    {},
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function getSessions(_token?: string): Promise<Session[]> {
  const response = await axios.get(`/api/v1/self/sessions`, {
    withCredentials: true,
  });
  return response.data;
}

export async function logoutSession(
  sessionId: string,
  _token?: string
): Promise<{ success: boolean; message: string }> {
  const response = await axios.post(
    `/api/v1/self/sessions/${sessionId}/logout`,
    {},
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function getApps(_token?: string): Promise<App[]> {
  const response = await axios.get(`/api/v1/self/apps`, {
    withCredentials: true,
  });
  return response.data;
}
