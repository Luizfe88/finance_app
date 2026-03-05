/// <reference types="vite/client" />
// API base URL — points to FastAPI backend
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const activeUserId = localStorage.getItem('activeUserId') || 'demo-user';
  
  const headers: Record<string, string> = { 
    'Content-Type': 'application/json',
    ...options.headers as any
  };

  // Add X-User-Id for dev mode
  headers['X-User-Id'] = activeUserId;

  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null as any;
  return res.json();
}

export interface TransactionCreate {
  account_id: string;
  amount: number;
  description: string;
  category: string;
  date: string;
  transaction_type: 'CREDIT' | 'DEBIT' | 'TRANSFER';
  payment_method?: string;
  installment_count?: number;
  is_recurring?: boolean;
  is_paid?: boolean;
  recurrence_rule?: string;
  envelope_id?: string;
  memo?: string;
}

export interface TransferCreate {
  from_account_id: string;
  to_account_id: string;
  amount: number;
  date: string;
  description: string;
  category: string;
  memo?: string;
}

export interface Account {
  id: string;
  user_id: string;
  bank_name: string;
  bank_code?: string;
  masked_account_number: string;
  account_type: string;
  balance: number;
  currency: string;
  is_active: boolean;
  invoice_due_day?: number;
  invoice_closing_day?: number;
  credit_limit?: number;
  created_at: string;
}

// ── Service Definition ────────────────────────────────────────────────────────
export const api = {
  transactions: {
    list: (params: any = {}) => {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '') as any
      ).toString();
      return request<any>(`/transactions${q ? '?' + q : ''}`);
    },
    create: (body: TransactionCreate) => request<any>('/transactions', { method: 'POST', body: JSON.stringify(body) }),
    execute: (id: string) => request<any>(`/transactions/${id}/execute`, { method: 'POST' }),
    transfer: (body: TransferCreate) => request<any[]>('/transactions/transfer', { method: 'POST', body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/transactions/${id}`, { method: 'DELETE' }),
  },

  dashboard: {
    get: (params: any = {}) => {
      const q = new URLSearchParams(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== null) as any
      ).toString();
      return request<any>(`/dashboard${q ? '?' + q : ''}`);
    },
    v2: (month?: string) => request<any>(`/dashboard/v2${month ? `?month=${month}` : ''}`),
  },

  budget: {
    envelopes: (month?: string) => request<any[]>(`/budget/envelopes${month ? `?month=${month}` : ''}`),
    createEnvelope: (body: any) => request<any>('/budget/envelopes', { method: 'POST', body: JSON.stringify(body) }),
    allocate: (body: any) => request<any>('/budget/allocate', { method: 'POST', body: JSON.stringify(body) }),
    readyToAssign: (month?: string) => request<any>(`/budget/ready-to-assign${month ? `?month=${month}` : ''}`),
    ensureSystem: (month?: string) => request<void>(`/budget/ensure-system${month ? `?month=${month}` : ''}`, { method: 'POST' }),
  },

  accounts: {
    list: () => request<Account[]>('/accounts'),
    create: (body: any) => request<Account>('/accounts', { method: 'POST', body: JSON.stringify(body) }),
    update: (id: string, body: any) => request<Account>(`/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/accounts/${id}`, { method: 'DELETE' }),
  },
  
  // Auth endpoints (JWT)
  auth: {
    token: (form: FormData) => request<any>('/auth/token', { method: 'POST', body: form }),
    register: (body: any) => request<any>('/auth/register', { method: 'POST', body: JSON.stringify(body) }),
    me: () => request<any>('/auth/me'),
  },

  users: {
    list: () => request<any[]>('/users'),
    create: (body: { email: string; name: string }) => request<any>('/users', { method: 'POST', body: JSON.stringify(body) }),
  }
};
