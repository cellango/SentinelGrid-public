"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/Header";
import { getDashboardStats, getAlerts, getIncidents, type DashboardStats, type Alert, type Incident } from "@/lib/api/dashboard";
import OnboardingBanner from "@/components/dashboard/OnboardingBanner";
import CloudConnections from "@/components/dashboard/CloudConnections";
import AgentStatus from "@/components/dashboard/AgentStatus";
import GitSecurityStatus from "@/components/dashboard/GitSecurityStatus";

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [signupCompleted, setSignupCompleted] = useState<boolean | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState<any>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);
  const hasFetchedData = useRef(false); // Track if we've already fetched data
  const hasInitialized = useRef(false); // Track if we've initialized

  // Single useEffect to handle all initialization
  useEffect(() => {
    // Prevent multiple initializations
    if (hasInitialized.current) {
      console.log('[Dashboard] Already initialized, skipping...');
      return;
    }
    hasInitialized.current = true;

    console.log('[Dashboard] Starting initialization...');
    
    // Check authentication and signup status
    const accessToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    if (!accessToken) {
      console.log('[Dashboard] No access token, redirecting to login');
      setLoading(false);
      router.push('/login');
      return;
    }

    // Load user info
    const storedTenantId = localStorage.getItem('tenant_id');
    const storedUser = localStorage.getItem('user');
    if (storedTenantId) setTenantId(storedTenantId);
    if (storedUser) {
      try {
        setUserInfo(JSON.parse(storedUser));
      } catch (e) {
        console.error('[Dashboard] Error parsing user info:', e);
      }
    }

    // Check signup completion
    const loginResponse = localStorage.getItem('login_response');
    let completed = true; // Default to true
    
    if (loginResponse) {
      try {
        const response = JSON.parse(loginResponse);
        completed = response.signup_completed !== false;
      } catch (e) {
        console.error('[Dashboard] Error parsing login response:', e);
      }
    }

    // Set state once, then fetch data if completed
    setSignupCompleted(completed);
    setLoading(false);

    if (!completed) {
      console.log('[Dashboard] Signup not completed, redirecting to signup page');
      router.push('/signup?step=2');
      return;
    }

    // Fetch dashboard data immediately if signup is completed
    if (completed && !hasFetchedData.current) {
      hasFetchedData.current = true;
      fetchDashboardData();
    }

    async function fetchDashboardData() {
      console.log('[Dashboard] Starting to fetch dashboard data...');
      setDataLoading(true);
      setDataError(null);
      
      try {
        const [statsData, alertsData, incidentsData] = await Promise.allSettled([
          getDashboardStats().catch(err => {
            console.error('[Dashboard] Error in getDashboardStats:', err);
            throw err;
          }),
          getAlerts(10).catch(err => {
            console.warn('[Dashboard] Failed to fetch alerts:', err);
            return { items: [], total: 0 };
          }),
          getIncidents(10).catch(err => {
            console.warn('[Dashboard] Failed to fetch incidents:', err);
            return { items: [], total: 0 };
          }),
        ]);
        
        console.log('[Dashboard] API calls completed');
        
        if (statsData.status === 'fulfilled') {
          setStats(statsData.value);
        } else {
          setStats({ active_alerts: 0, incidents: 0, findings: 0 });
        }
        
        if (alertsData.status === 'fulfilled') {
          setAlerts(alertsData.value.items || []);
        } else {
          setAlerts([]);
        }
        
        if (incidentsData.status === 'fulfilled') {
          setIncidents(incidentsData.value.items || []);
        } else {
          setIncidents([]);
        }
      } catch (error: any) {
        console.error('[Dashboard] Error fetching dashboard data:', error);
        setDataError(error.message || 'Failed to load dashboard data');
        setStats({ active_alerts: 0, incidents: 0, findings: 0 });
        setAlerts([]);
        setIncidents([]);
      } finally {
        setDataLoading(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty deps - only run once on mount

  if (loading) {
    console.log('[Dashboard] Rendering loading state');
    return (
      <main className="min-h-screen bg-slate-950 text-slate-50">
        <Header />
        <div className="flex items-center justify-center min-h-[80vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
            <p className="text-slate-300">Loading...</p>
          </div>
        </div>
      </main>
    );
  }

  console.log('[Dashboard] Rendering dashboard - signupCompleted:', signupCompleted, 'dataLoading:', dataLoading, 'dataError:', dataError);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Onboarding Banner */}
        <OnboardingBanner />
        <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
        
        {/* Account Information */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Account Information</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {userInfo && (
              <div>
                <p className="text-sm text-slate-400 mb-1">Email</p>
                <p className="text-slate-200">{userInfo.email}</p>
              </div>
            )}
            {tenantId && (
              <div>
                <p className="text-sm text-slate-400 mb-1">Tenant ID</p>
                <p className="text-slate-200 font-mono text-sm">{tenantId}</p>
              </div>
            )}
            {userInfo?.roles && userInfo.roles.length > 0 && (
              <div>
                <p className="text-sm text-slate-400 mb-1">Roles</p>
                <div className="flex flex-wrap gap-2">
                  {userInfo.roles.map((role: string, idx: number) => (
                    <span key={idx} className="px-2 py-1 bg-cyan-500/20 text-cyan-300 rounded text-xs">
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dashboard Stats */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Security Overview</h2>
          {dataLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400 mx-auto mb-4"></div>
              <p className="text-slate-400">Loading security data...</p>
            </div>
          ) : dataError ? (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
              <p className="text-red-300 text-sm">{dataError}</p>
              <p className="text-slate-400 text-xs mt-2">Some features may not be available until data sources are connected.</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-3 gap-4">
              <div className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-2xl font-bold text-cyan-400 mb-2">
                  {stats?.active_alerts ?? 0}
                </p>
                <p className="text-sm text-slate-400">Active Alerts</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-2xl font-bold text-cyan-400 mb-2">
                  {stats?.incidents ?? 0}
                </p>
                <p className="text-sm text-slate-400">Incidents</p>
              </div>
              <div className="bg-slate-800/50 rounded-lg p-4">
                <p className="text-2xl font-bold text-cyan-400 mb-2">
                  {stats?.findings ?? 0}
                </p>
                <p className="text-sm text-slate-400">Findings</p>
              </div>
            </div>
          )}
        </div>

        {/* Recent Alerts */}
        {!dataLoading && alerts.length > 0 && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
            <div className="space-y-3">
              {alerts.slice(0, 5).map((alert) => (
                <div key={alert.id} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-slate-200 font-medium mb-1">{alert.title}</h3>
                      {alert.description && (
                        <p className="text-sm text-slate-400 mb-2">{alert.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span>Severity: {alert.raw_severity}</span>
                        <span>Status: {alert.status}</span>
                        {alert.detection_time && (
                          <span>{new Date(alert.detection_time).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${
                      alert.raw_severity === 'critical' ? 'bg-red-500/20 text-red-300' :
                      alert.raw_severity === 'high' ? 'bg-orange-500/20 text-orange-300' :
                      alert.raw_severity === 'medium' ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-blue-500/20 text-blue-300'
                    }`}>
                      {alert.raw_severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Incidents */}
        {!dataLoading && incidents.length > 0 && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Recent Incidents</h2>
            <div className="space-y-3">
              {incidents.slice(0, 5).map((incident) => (
                <div key={incident.id} className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-slate-200 font-medium mb-1">{incident.title}</h3>
                      <div className="flex items-center gap-4 text-xs text-slate-500 mt-2">
                        <span>Status: {incident.status}</span>
                        <span>Severity: {incident.severity}</span>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs ${
                      incident.severity === 'critical' ? 'bg-red-500/20 text-red-300' :
                      incident.severity === 'high' ? 'bg-orange-500/20 text-orange-300' :
                      incident.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-300' :
                      'bg-blue-500/20 text-blue-300'
                    }`}>
                      {incident.severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!dataLoading && !dataError && alerts.length === 0 && incidents.length === 0 && (
          <div className="bg-slate-900/70 border border-slate-800 rounded-lg p-6">
            <div className="text-center py-12">
              <p className="text-slate-400 mb-4">
                No alerts or incidents yet. Connect your data sources to see security insights.
              </p>
              <p className="text-xs text-slate-500">
                Once connected, you&apos;ll see your first security insights within a few hours.
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

