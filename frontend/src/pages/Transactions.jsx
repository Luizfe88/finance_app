import { useEffect, useState, useCallback } from 'react';
import { api } from '../services/api';

const fmtDate = (d) => new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
const fmtCur  = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);

const CATEGORIES = [
  'Todos', 'Alimentação', 'Transporte', 'Moradia', 'Saúde',
  'Educação', 'Lazer', 'Roupas', 'Serviços', 'Outros'
];

const TXN_ICONS = {
  'Alimentação': '🍽️', 'Transporte': '🚗', 'Moradia': '🏠',
  'Saúde': '💊', 'Educação': '📚', 'Lazer': '🎬',
  'Roupas': '👕', 'Serviços': '⚡', 'Outros': '💳',
};

function SkeletonRow() {
  return (
    <div className="txn-row" style={{ cursor: 'default' }}>
      <div className="skeleton" style={{ width: 42, height: 42, borderRadius: '50%', flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div className="skeleton" style={{ height: 14, width: '55%', marginBottom: 6 }} />
        <div className="skeleton" style={{ height: 11, width: '35%' }} />
      </div>
      <div className="skeleton" style={{ height: 16, width: 90 }} />
    </div>
  );
}

export default function Transactions() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch]   = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage]       = useState(0);
  const [deleting, setDeleting] = useState(null);
  const [toast, setToast]     = useState(null);

  const LIMIT = 20;

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        limit: LIMIT,
        offset: page * LIMIT,
        ...(category ? { category } : {}),
      };
      const res = await api.transactions.list(params);
      setData(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [page, category]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id) => {
    if (!window.confirm('Excluir esta transação?')) return;
    setDeleting(id);
    try {
      await api.transactions.delete(id);
      showToast('✅ Transação excluída');
      load();
    } catch (e) {
      showToast('❌ Erro ao excluir');
    } finally {
      setDeleting(null);
    }
  };

  // Client-side search filter
  const filtered = data?.items?.filter(t =>
    !search || t.description?.toLowerCase().includes(search.toLowerCase())
  ) || [];

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Transações</h1>
          <p className="page-subtitle">
            {data ? `${data.total} transações no total` : '...'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            className="input"
            placeholder="Buscar por descrição..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="input"
          style={{ width: 180 }}
          value={category}
          onChange={e => { setCategory(e.target.value === 'Todos' ? '' : e.target.value); setPage(0); }}
        >
          {CATEGORIES.map(c => <option key={c}>{c}</option>)}
        </select>
      </div>

      {/* Transaction List */}
      <div className="card">
        <div className="txn-list">
          {loading ? (
            [1,2,3,4,5].map(i => <SkeletonRow key={i} />)
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📭</div>
              <p>Nenhuma transação encontrada.</p>
              <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)' }}>
                Importe um extrato bancário na página <strong>Importar</strong>.
              </p>
            </div>
          ) : (
            filtered.map(t => {
              const isCredit = t.transaction_type === 'CREDIT';
              return (
                <div key={t.id} className="txn-row" style={{ position: 'relative' }}>
                  <div className={`txn-icon ${isCredit ? 'credit' : 'debit'}`}>
                    {TXN_ICONS[t.category] || '💳'}
                  </div>
                  <div className="txn-info">
                    <p className="txn-description">{t.description || '—'}</p>
                    <p className="txn-meta">
                      {t.category} &nbsp;·&nbsp; {fmtDate(t.date)}
                      {t.payee ? ` · ${t.payee}` : ''}
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className={`txn-amount ${isCredit ? 'credit' : 'debit'}`}>
                      {isCredit ? '+' : '-'}{fmtCur(t.amount)}
                    </span>
                    <span
                      className={`badge ${isCredit ? 'badge-income' : 'badge-expense'}`}
                      style={{ fontSize: 10 }}
                    >
                      {isCredit ? 'Crédito' : 'Débito'}
                    </span>
                    <button
                      onClick={() => handleDelete(t.id)}
                      disabled={deleting === t.id}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', fontSize: 16, padding: '4px',
                        borderRadius: 4, transition: 'color 150ms',
                      }}
                      title="Excluir"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Pagination */}
        {data && data.total > LIMIT && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
            <button className="btn btn-ghost" onClick={() => setPage(p => Math.max(0, p-1))} disabled={page === 0}>
              ← Anterior
            </button>
            <span style={{ color: 'var(--text-muted)', fontSize: 13, alignSelf: 'center' }}>
              Página {page + 1} de {Math.ceil(data.total / LIMIT)}
            </span>
            <button className="btn btn-ghost" onClick={() => setPage(p => p+1)} disabled={!data.has_more}>
              Próxima →
            </button>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="toast">
          <span className="toast-icon">{toast.startsWith('✅') ? '✅' : '❌'}</span>
          <span className="toast-msg">{toast.replace(/^[✅❌]\s/, '')}</span>
        </div>
      )}
    </div>
  );
}
