import { 
  SystemStatus, 
  DashboardMetrics, 
  Transaction, 
  AuditEvent, 
  ApprovalItem,
  DemoScenarioResult
} from '../types';

// Resolve API base URL dynamically:
// 1. Uses explicit VITE_API_URL environment variable if defined.
// 2. Otherwise defaults to same-origin '/api' — the Vercel rewrite (vercel.json)
//    proxies it to the backend in production, and the Vite dev server proxies it
//    locally. Same-origin everywhere means there is no cross-origin CORS to configure.
const getApiBase = (): string => {
  const envUrl = (import.meta as any).env?.VITE_API_URL;
  if (envUrl && envUrl.trim() !== '') {
    const cleanUrl = envUrl.trim().replace(/\/+$/, '');
    return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
  }
  return '/api';
};

export const API_BASE = getApiBase();

export async function fetchHealth(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch system health');
  return res.json();
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE}/dashboard`);
  if (!res.ok) throw new Error('Failed to fetch dashboard metrics');
  return res.json();
}

export async function fetchTransactions(params?: { 
  status?: string; 
  failure_reason?: string; 
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<{ items: Transaction[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.failure_reason) query.append('failure_reason', params.failure_reason);
  if (params?.search) query.append('search', params.search);
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset) query.append('offset', params.offset.toString());

  const res = await fetch(`${API_BASE}/transactions?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function fetchTransactionById(id: string): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/transactions/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch transaction ${id}`);
  return res.json();
}

export async function analyzeTransaction(id: string) {
  const res = await fetch(`${API_BASE}/agent/analyze/${id}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to analyze transaction ${id}`);
  return res.json();
}

export async function executeRecovery(id: string) {
  const res = await fetch(`${API_BASE}/recovery/execute/${id}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to execute recovery for transaction ${id}`);
  return res.json();
}

export async function approveRecoveryAction(actionId: string) {
  const res = await fetch(`${API_BASE}/recovery/approve/${actionId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to approve action ${actionId}`);
  return res.json();
}

export async function rejectRecoveryAction(actionId: string, reason?: string) {
  const res = await fetch(`${API_BASE}/recovery/reject/${actionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason: reason || 'Merchant manually rejected' }),
  });
  if (!res.ok) throw new Error(`Failed to reject action ${actionId}`);
  return res.json();
}

export async function fetchApprovals(): Promise<ApprovalItem[]> {
  const res = await fetch(`${API_BASE}/approvals`);
  if (!res.ok) throw new Error('Failed to fetch approvals');
  return res.json();
}

export async function fetchAuditTrail(params?: { 
  transaction_id?: string; 
  limit?: number;
}): Promise<AuditEvent[]> {
  const query = new URLSearchParams();
  if (params?.transaction_id) query.append('transaction_id', params.transaction_id);
  if (params?.limit) query.append('limit', (params.limit || 100).toString());

  const res = await fetch(`${API_BASE}/audit?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function runSimulation(): Promise<any> {
  const res = await fetch(`${API_BASE}/simulation/run`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to run simulation');
  return res.json();
}

export async function runDemoScenario(
  scenarioKey: string, 
  mode?: 'TEST_MODE' | 'SIMULATION_MODE'
): Promise<DemoScenarioResult> {
  const url = `${API_BASE}/demo/scenario`;
  const payload: Record<string, any> = { scenario: scenarioKey, scenario_id: scenarioKey };
  if (mode) {
    payload.mode = mode;
  }
  console.log(`[RecoverIQ Network] Dispatching POST ${url}`, payload);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    console.log(`[RecoverIQ Network] POST ${url} status:`, res.status);
    if (!res.ok) {
      const errText = await res.text();
      let errorMsg = `Server error ${res.status}`;
      try {
        const parsed = JSON.parse(errText);
        errorMsg = parsed.detail || parsed.message || errorMsg;
      } catch {
        if (errText) errorMsg = errText;
      }
      throw new Error(errorMsg);
    }
    return res.json();
  } catch (err: any) {
    console.error(`[RecoverIQ Error] Failed to run scenario ${scenarioKey}:`, err);
    if (err.name === 'TypeError' && err.message?.toLowerCase().includes('fetch')) {
      throw new Error('Unable to connect to RecoverIQ backend. Please verify that the backend API is online.');
    }
    throw err;
  }
}

export async function reseedDatabase(): Promise<any> {
  const res = await fetch(`${API_BASE}/seed?force=true`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reseed database');
  return res.json();
}

