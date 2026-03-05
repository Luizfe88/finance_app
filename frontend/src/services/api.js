// API base URL — points to FastAPI backend
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Transactions ──────────────────────────────────────────────────────────────
export const api = {
  transactions: {
    list: (params = {}) => {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
      ).toString();
      return request(`/transactions${q ? '?' + q : ''}`);
    },
    create: (body) => request('/transactions', { method: 'POST', body: JSON.stringify(body) }),
    delete: (id) => request(`/transactions/${id}`, { method: 'DELETE' }),
  },

  // ── Dashboard ────────────────────────────────────────────────────────────────
  dashboard: {
    get: (params = {}) => {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null)
      ).toString();
      return request(`/dashboard${q ? '?' + q : ''}`);
    },
    v2: (month) => request(`/dashboard/v2${month ? `?month=${month}` : ''}`),
  },

  // ── Budget / ZBB ──────────────────────────────────────────────────────────────
  budget: {
    envelopes: (month) => request(`/budget/envelopes${month ? `?month=${month}` : ''}`),
    createEnvelope: (body) => request('/budget/envelopes', { method: 'POST', body: JSON.stringify(body) }),
    allocate: (body) => request('/budget/allocate', { method: 'POST', body: JSON.stringify(body) }),
    readyToAssign: (month) => request(`/budget/ready-to-assign${month ? `?month=${month}` : ''}`),
    ensureSystem: (month) => request(`/budget/ensure-system${month ? `?month=${month}` : ''}`, { method: 'POST' }),
  },

  // ── Installments ─────────────────────────────────────────────────────────────
  installments: {
    list: () => request('/installments'),
    create: (body) => request('/installments', { method: 'POST', body: JSON.stringify(body) }),
    projection: () => request('/installments/projection'),
    cancel: (id) => request(`/installments/${id}/cancel`, { method: 'POST' }),
  },

  // ── Subscriptions ─────────────────────────────────────────────────────────────
  subscriptions: {
    list: () => request('/subscriptions'),
    create: (body) => request('/subscriptions', { method: 'POST', body: JSON.stringify(body) }),
    update: (id, body) => request(`/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    cancel: (id) => request(`/subscriptions/${id}`, { method: 'DELETE' }),
    runBilling: (dryRun = false) => request(`/subscriptions/run-billing?dry_run=${dryRun}`, { method: 'POST' }),
  },

  // ── Audit Trail ──────────────────────────────────────────────────────────────
  audit: {
    events: (limit = 50, offset = 0) => request(`/audit/events?limit=${limit}&offset=${offset}`),
    verify: () => request('/audit/verify'),
  },

  // ── Import ───────────────────────────────────────────────────────────────────
  import: {
    ofx: (file, accountId) => {
      const form = new FormData();
      form.append('file', file);
      form.append('account_id', accountId);
      return request('/import/ofx', { method: 'POST', body: form, headers: {} });
    },
    csv: (file, accountId, bankPreset) => {
      const form = new FormData();
      form.append('file', file);
      form.append('account_id', accountId);
      if (bankPreset) form.append('bank_preset', bankPreset);
      return request('/import/csv', { method: 'POST', body: form, headers: {} });
    },
  },

  // ── Accounts ─────────────────────────────────────────────────────────────────
  accounts: {
    list: () => request('/accounts'),
    create: (body) => request('/accounts', { method: 'POST', body: JSON.stringify(body) }),
    delete: (id) => request(`/accounts/${id}`, { method: 'DELETE' }),
  },
};
