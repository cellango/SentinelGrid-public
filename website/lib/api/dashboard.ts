/**
 * Dashboard API client
 * Handles fetching dashboard data from API Gateway
 */

// API Gateway URL - should be accessible from browser
// In production, this would be https://api.sentinelgrid.ai
// In dev, nginx proxies to API Gateway on port 8082
// API Gateway URL - should be accessible from browser
// In production, this would be https://api.sentinelgrid.ai
// In dev, nginx proxies /api to API Gateway
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE || 
  (typeof window !== 'undefined' && window.location.origin.includes('localhost:3443') 
    ? `${window.location.origin}/api`  // Use nginx proxy for HTTPS (same origin)
    : 'http://localhost:8082');

export interface Alert {
  id: string;
  source: string;
  external_id?: string;
  title: string;
  description?: string;
  raw_severity: string;
  status: string;
  detection_time: string;
  asset_id?: string;
  user_identifier?: string;
  last_ai_analysis?: {
    id: string;
    ai_severity: string;
    ai_category?: string;
    ai_confidence?: number;
  };
}

export interface Incident {
  id: string;
  source: string;
  external_id?: string;
  title: string;
  status: string;
  severity: string;
  latest_ai_summaries?: {
    analyst?: { id: string; created_at: string };
    executive?: { id: string; created_at: string };
  };
}

export interface DashboardStats {
  active_alerts: number;
  incidents: number;
  findings: number;
  alerts_by_severity?: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

/**
 * Get access token from storage
 */
function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

/**
 * Fetch alerts for the dashboard
 */
export async function getAlerts(limit: number = 10): Promise<{ items: Alert[]; total: number }> {
  const token = getAccessToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  // API_BASE_URL already includes /api if using nginx proxy, so check and adjust
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/alerts?limit=${limit}`
    : `${API_BASE_URL}/api/v1/alerts?limit=${limit}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch alerts: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Fetch incidents for the dashboard
 */
export async function getIncidents(limit: number = 10): Promise<{ items: Incident[]; total: number }> {
  const token = getAccessToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  // API_BASE_URL already includes /api if using nginx proxy, so check and adjust
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/incidents?limit=${limit}`
    : `${API_BASE_URL}/api/v1/incidents?limit=${limit}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Authentication required');
    }
    throw new Error(`Failed to fetch incidents: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get dashboard statistics
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  const token = getAccessToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  try {
    // Fetch alerts to calculate stats
    const alertsData = await getAlerts(100);
    const incidentsData = await getIncidents(100);

    const activeAlerts = alertsData.items.filter(a => a.status === 'open' || a.status === 'triaged').length;
    const alertsBySeverity = {
      critical: alertsData.items.filter(a => a.raw_severity === 'critical' || a.last_ai_analysis?.ai_severity === 'critical').length,
      high: alertsData.items.filter(a => a.raw_severity === 'high' || a.last_ai_analysis?.ai_severity === 'high').length,
      medium: alertsData.items.filter(a => a.raw_severity === 'medium' || a.last_ai_analysis?.ai_severity === 'medium').length,
      low: alertsData.items.filter(a => a.raw_severity === 'low' || a.last_ai_analysis?.ai_severity === 'low').length,
    };

    return {
      active_alerts: activeAlerts,
      incidents: incidentsData.total,
      findings: 0, // TODO: Add findings endpoint
      alerts_by_severity: alertsBySeverity,
    };
  } catch (error) {
    console.error('Error fetching dashboard stats:', error);
    // Return default stats on error
    return {
      active_alerts: 0,
      incidents: 0,
      findings: 0,
    };
  }
}

