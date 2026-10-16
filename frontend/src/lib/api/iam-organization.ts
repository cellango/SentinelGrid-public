/**
 * IAM Organization API
 */

import axios from 'axios';

const API_BASE = '';

export interface Organization {
  name: string;
  display_name?: string;
  logo_url?: string;
  primary_domain?: string;
  domains: string[];
  timezone?: string;
  language?: string;
  contact_email?: string;
  created_at?: string;
  updated_at?: string;
}

export interface OrganizationUpdate {
  name?: string;
  display_name?: string;
  primary_domain?: string;
  domains?: string[];
  timezone?: string;
  language?: string;
  contact_email?: string;
}

export async function getOrganization(_token?: string): Promise<Organization> {
  const response = await axios.get(`${API_BASE}/api/v1/organization`, {
    withCredentials: true,
  });
  return response.data;
}

export async function updateOrganization(
  data: OrganizationUpdate,
  _token?: string
): Promise<Organization> {
  const response = await axios.put(
    `${API_BASE}/api/v1/organization`,
    data,
    {
      withCredentials: true,
    }
  );
  return response.data;
}

export async function uploadLogo(
  file: File,
  _token?: string
): Promise<{ success: boolean; logo_url: string; message: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(
    `${API_BASE}/api/v1/organization/logo`,
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
