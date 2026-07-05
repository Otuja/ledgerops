const BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');

export const fetchStats = async () => {
  const res = await fetch(`${BASE_URL}/stats/`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
};

export const fetchLogs = async () => {
  const res = await fetch(`${BASE_URL}/logs/`);
  if (!res.ok) throw new Error('Failed to fetch logs');
  return res.json();
};

export const fetchWallets = async () => {
  const res = await fetch(`${BASE_URL}/wallets/`);
  if (!res.ok) throw new Error('Failed to fetch wallets');
  return res.json();
};

export const fetchNegotiations = async () => {
  const res = await fetch(`${BASE_URL}/negotiations/`);
  if (!res.ok) throw new Error('Failed to fetch negotiations');
  return res.json();
};

export const fetchHealth = async () => {
  try {
    const res = await fetch(`${BASE_URL}/health/`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch (err) {
    return false;
  }
};

export const fetchTrustScore = async (agentId) => {
  const res = await fetch(`${BASE_URL}/trust-score/${encodeURIComponent(agentId)}/`);
  if (!res.ok) throw new Error('Failed to fetch trust score');
  return res.json();
};

export const fetchTrustLookups = async () => {
  const res = await fetch(`${BASE_URL}/trust-lookups/`);
  if (!res.ok) throw new Error('Failed to fetch trust lookups');
  return res.json();
};

export const executeService = async (serviceType, targetAgentId = '') => {
  const res = await fetch(`${BASE_URL}/execute-service/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service_type: serviceType, target_agent_id: targetAgentId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Failed to execute service');
  return data;
};
