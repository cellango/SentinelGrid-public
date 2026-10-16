/**
 * Endpoint Agents API Client
 * Handles agent management and selection
 */

import { apiClient } from './client';

// ============================================================================
// Type Definitions
// ============================================================================

export interface EndpointAgent {
  id: string;
  name: string;
  version: string;
  os_type: 'linux' | 'windows' | 'macos';
  os_name: string;
  os_version: string;
  architecture: 'x86_64' | 'arm64';
  status: 'online' | 'offline' | 'degraded' | 'unknown';
  last_seen: string;
  server_name?: string;
  server_id?: string;
  environment?: 'prod' | 'staging' | 'dev';
  installed_at: string;
  health_score?: number; // 0-100
}

export interface AgentInstaller {
  os_type: string;
  os_name: string;
  architecture: string;
  download_url: string;
  checksum?: string;
  install_command?: string;
  version: string;
  file_size_bytes?: number;
}

export interface AgentInstallConfig {
  server_name: string;
  server_id?: string;
  os_type: 'linux' | 'windows' | 'macos';
  os_name: string;
  os_version: string;
  architecture: 'x86_64' | 'arm64';
  environment?: 'prod' | 'staging' | 'dev';
  agent_version?: string; // Optional, defaults to latest
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * List all endpoint agents
 */
export async function listAgents(tenantId: string): Promise<EndpointAgent[]> {
  const response = await apiClient.get<{ agents: EndpointAgent[] }>(
    `/agents`
  );
  return response.data.agents;
}

/**
 * Get agent details
 */
export async function getAgent(agentId: string, tenantId: string): Promise<EndpointAgent> {
  const response = await apiClient.get<EndpointAgent>(
    `/agents/${agentId}`
  );
  return response.data;
}

/**
 * Get agent status
 */
export async function getAgentStatus(agentId: string, tenantId: string): Promise<{
  status: string;
  health_score: number;
  last_seen: string;
  metrics?: Record<string, any>;
}> {
  const response = await apiClient.get(
    `/agents/${agentId}/status`
  );
  return response.data;
}

/**
 * Install agent on a server
 */
export async function installAgent(
  config: AgentInstallConfig,
  tenantId: string
): Promise<{
  agent_id: string;
  install_command: string;
  download_url?: string;
  instructions?: string;
}> {
  const response = await apiClient.post(
    `/agents/install`,
    config
  );
  return response.data;
}

/**
 * Update agent version
 */
export async function updateAgent(
  agentId: string,
  version: string,
  tenantId: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post(
    `/agents/${agentId}/update`,
    { version }
  );
  return response.data;
}

/**
 * Remove/uninstall agent
 */
export async function removeAgent(
  agentId: string,
  tenantId: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete(
    `/agents/${agentId}`
  );
  return response.data;
}

/**
 * Download agent installer
 */
export async function downloadAgentInstaller(
  osType: string,
  architecture: string,
  tenantId: string
): Promise<AgentInstaller> {
  const response = await apiClient.get<AgentInstaller>(
    `/agents/installers/${osType}/${architecture}`
  );
  return response.data;
}

/**
 * Get available agent versions
 */
export async function getAgentVersions(tenantId: string): Promise<{
  latest: string;
  versions: string[];
}> {
  const response = await apiClient.get(
    `/agents/versions`
  );
  return response.data;
}

