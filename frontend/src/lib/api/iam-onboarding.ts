/**
 * IAM User Onboarding API
 */

import axios from 'axios';

// Use relative URLs so requests go through the same origin (avoids mixed-content/CORS issues)
// and leverage Next.js rewrites to reach the IAM Agent.
const API_BASE = '';

export interface UserInviteRequest {
  email: string;
  firstName?: string;
  lastName?: string;
  role?: string;
  send_email?: boolean;
  expires_in_days?: number;
}

export interface UserInviteResponse {
  invitation_id: string;
  email: string;
  invitation_token: string;
  expires_at: string;
  status: string;
}

export interface InvitationListResponse {
  items: UserInviteResponse[];
  total: number;
}

export interface BulkUploadResponse {
  total_rows: number;
  successful: number;
  failed: number;
  errors: Array<{
    row: number;
    email: string;
    error: string;
  }>;
}

export async function inviteUser(
  inviteData: UserInviteRequest,
  _token?: string
): Promise<UserInviteResponse> {
  const response = await axios.post(
    `${API_BASE}/api/v1/users/invite`,
    inviteData,
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function listInvitations(
  _token?: string,
  status?: string,
  page: number = 1,
  limit: number = 50
): Promise<InvitationListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });
  if (status) {
    params.append('status', status);
  }

  const response = await axios.get(
    `${API_BASE}/api/v1/users/invitations?${params.toString()}`,
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function bulkUploadUsers(
  file: File,
  _token?: string
): Promise<BulkUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(
    `${API_BASE}/api/v1/users/bulk-upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      withCredentials: true,
    }
  );
  return response.data;
}

export async function cancelInvitation(
  invitationId: string,
  _token?: string
): Promise<void> {
  await axios.delete(`${API_BASE}/api/v1/users/invitations/${invitationId}`, {
    withCredentials: true,
  });
}
