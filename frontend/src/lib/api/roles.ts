import { apiClient } from './client';

export interface TenantRole {
  id: string;
  name: string;
  description?: string | null;
  composite?: boolean;
}

export const rolesApi = {
  list: async (): Promise<TenantRole[]> => {
    const response = await apiClient.get('/v1/roles');
    return response.data;
  },
};
