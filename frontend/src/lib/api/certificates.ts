/**
 * Certificate Service API Client
 * PKI certificate management (not IAM certifications)
 */

import { apiClient } from './client';

export interface Certificate {
  id: string;
  tenant_id: string;
  ca_authority_id: string;
  common_name: string;
  serial_number: string;
  status: 'active' | 'revoked' | 'expired';
  certificate_pem?: string;
  private_key_pem?: string;
  issued_at: string;
  expires_at: string;
  revoked_at?: string;
  revocation_reason?: string;
  created_at: string;
  updated_at: string;
}

export interface CertificateRequest {
  id: string;
  tenant_id: string;
  common_name: string;
  subject_alternative_names?: string[];
  certificate_type: 'private' | 'public';
  ca_authority_id?: string;
  status: 'pending' | 'issued' | 'failed';
  created_at: string;
}

export interface CAAuthority {
  id: string;
  tenant_id?: string;
  name: string;
  type: 'ejbca' | 'step-ca' | 'aws-acm-pca';
  status: 'active' | 'disabled';
  created_at: string;
}

export interface CertificateFilters {
  status?: 'active' | 'revoked' | 'expired';
  ca_authority_id?: string;
  common_name?: string;
  limit?: number;
  offset?: number;
}

export interface EnrollmentProtocol {
  name: string;
  version: string;
  directory_url?: string;
  endpoint_url?: string;
  cacerts_url?: string;
  simpleenroll_url?: string;
  simplereenroll_url?: string;
  use_cases: string[];
  endpoint: string;
}

export interface ACMEDirectory {
  directory_url: string;
  new_account_url: string;
  new_order_url: string;
  new_nonce_url: string;
  key_change_url: string;
  revoke_cert_url: string;
  meta?: {
    terms_of_service?: string;
    website?: string;
    caa_identities?: string[];
  };
}

export interface SCEPEndpoint {
  scep_endpoint_url: string;
  ca_certificate_url: string;
  instructions: {
    description: string;
    usage: string;
    password: string;
  };
}

export interface ESTEndpoints {
  cacerts_url: string;
  simpleenroll_url: string;
  simplereenroll_url: string;
  instructions: {
    description: string;
    usage: string;
    authentication: string;
  };
}

export const certificateApi = {
  // List certificates
  listCertificates: (filters?: CertificateFilters) =>
    apiClient.get<Certificate[]>('/certificates', { params: filters }),

  // Get certificate detail
  getCertificate: (id: string) =>
    apiClient.get<Certificate>(`/certificates/${id}`),

  // Request certificate (private or public)
  requestCertificate: (data: {
    common_name: string;
    subject_alternative_names?: string[];
    certificate_type: 'private' | 'public';
    ca_authority_id?: string;
    validity_days?: number;
  }) =>
    apiClient.post<Certificate>('/certificates/request', data),

  // Revoke certificate
  revokeCertificate: (id: string, reason?: string) =>
    apiClient.post(`/certificates/${id}/revoke`, { reason }),

  // Renew certificate
  renewCertificate: (id: string) =>
    apiClient.post<Certificate>(`/certificates/${id}/renew`),

  // Get CA chain
  getCAChain: (caId: string) =>
    apiClient.get<string>(`/ca/${caId}/chain`),

  // List CA authorities
  listCAs: () =>
    apiClient.get<CAAuthority[]>('/ca'),

  // Enrollment Protocols
  getACMEDirectory: (alias?: string) =>
    apiClient.get<ACMEDirectory>('/enrollment/acme/directory', {
      params: alias ? { alias } : undefined,
    }),

  getSCEPEndpoint: (raName?: string) =>
    apiClient.get<SCEPEndpoint>('/enrollment/scep/endpoint', {
      params: raName ? { ra_name: raName } : undefined,
    }),

  getESTEndpoints: (alias?: string) =>
    apiClient.get<ESTEndpoints>('/enrollment/est/cacerts', {
      params: alias ? { alias } : undefined,
    }),

  listEnrollmentProtocols: () =>
    apiClient.get<{ protocols: Record<string, EnrollmentProtocol> }>(
      '/enrollment/protocols'
    ),

  // Bootstrap tokens
  createBootstrapToken: (data: { agent_id?: string; ttl_hours?: number }) =>
    apiClient.post<{ token: string; expires_at: string }>(
      '/bootstrap-tokens',
      data
    ),
};

