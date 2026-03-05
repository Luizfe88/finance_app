import { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar,
} from 'recharts';
import { api } from '../services/api';

// ── Formatters ────────────────────────────────────────────────────────────────
const fmtBRL = (v) => new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v ?? 0);
const fmtPct = (v) => `${Number(v ?? 0).toFixed(1)}%`;
const fmtMonth = (m) => {
  if (!m) return '';
  const [y, mo] = m.split('-');
  return new Date(y, mo - 1).toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' });
};
const fmtDate = (d) => new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });

// ── Category icons ────────────────────────────────────────────────────────────
const ICONS = {
  Alimentação: '🍽️', Transporte: '🚗', Moradia: '🏠', Saúde: '💊',
  Educação: '📚', Lazer: '🎬', Roupas: '👕', Serviços: '⚡', Outros: '💳',
};

// ── Trend badge ───────────────────────────────────────────────────────────────
function TrendBadge({ vs_avg_pct, trend }) {
  if (vs_avg_pct === 0) return null;
  const isGood = (trend === 'UP' && vs_avg_pct > 0) || (trend === 'DOWN' && vs_avg_pct < 0);
  const color = isGood ? '#10B981' : '#F59E0B';
  const arrow = vs_avg_pct > 0 ? '▲' : '▼';
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, color,
      background: color + '20', borderRadius: 4,
      padding: '2px 7px', marginLeft: 6,
    }}>
      {arrow} {Math.abs(vs_avg_pct).toFixed(1)}% vs média
    </span>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KPICard({ kpi, isCurrency = true, accent }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVisible(true), 100); return () => clearTimeout(t); }, []);

  return (
    <div className="summary-card" style={{
      borderLeft: `4px solid ${accent || 'var(--accent)'}`,
      position: 'relative', overflow: 'hidden',
      opacity: visible ? 1 : 0, transform: visible ? 'translateY(0)' : 'translateY(12px)',
      transition: 'opacity 0.4s ease, transform 0.4s ease',
    }}>
      {kpi?.alert && (
        <div style={{
          position: 'absolute', top: 0, right: 0, left: 0, height: 2,
          background: 'linear-gradient(90deg, #F59E0B, #EF4444)', borderRadius: '0 0 0 0',
        }} />
      )}
      <span className="summary-label" style={{ display: 'flex', alignItems: 'center' }}>
        {kpi?.label}
        {kpi?.alert && <span style={{ marginLeft: 6, fontSize: 12 }}>⚡</span>}
      </span>
      <span className="summary-value" style={{ fontSize: '1.5rem', fontWeight: 800 }}>
        {isCurrency ? fmtBRL(kpi?.value) : fmtPct(kpi?.value)}
      </span>
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
        <TrendBadge vs_avg_pct={kpi?.vs_avg_pct} trend={kpi?.trend} />
        {kpi?.alert_message && (
          <span style={{ fontSize: 11, color: '#F59E0B', marginTop: 2 }}>{kpi.alert_message}</span>
        )}
      </div>
    </div>
  );
}

// ── Ready-to-Assign Banner ────────────────────────────────────────────────────
function ReadyToAssignBanner({ kpi }) {
  const [pulse, setPulse] = useState(true);
  if (!kpi?.alert || kpi.value <= 0) return null;
  return (
    <div style={{
      background: 'linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05))',
      border: '1px solid rgba(245,158,11,0.4)',
      borderRadius: 12, padding: '14px 20px', marginBottom: 24,
      display: 'flex', alignItems: 'center', gap: 16,
      animation: pulse ? 'subtlePulse 2s ease-in-out infinite' : 'none',
    }}>
      <span style={{ fontSize: 28 }}>📥</span>
      <div style={{ flex: 1 }}>
        <p style={{ color: '#F59E0B', fontWeight: 700, margin: 0, fontSize: 15 }}>
          Pronto para Atribuir: {fmtBRL(kpi.value)}
        </p>
        <p style={{ color: 'var(--text-secondary)', margin: '2px 0 0', fontSize: 13 }}>
          {kpi.alert_message}
        </p>
      </div>
      <button
        onClick={() => setPulse(false)}
        style={{
          background: 'rgba(245,158,11,0.2)', border: '1px solid rgba(245,158,11,0.5)',
          color: '#F59E0B', borderRadius: 8, padding: '8px 16px',
          cursor: 'pointer', fontWeight: 700, fontSize: 13,
        }}>
        Alocar →
      </button>
    </div>
  );
}

// ── Envelope Card ─────────────────────────────────────────────────────────────
function EnvelopeCard({ env }) {
  const pct = Math.min(env.utilization_pct, 100);
  const isOver = env.is_overspent;
  const barColor = isOver ? '#EF4444' : pct > 80 ? '#F59E0B' : env.color || '#6366F1';

  return (
    <div style={{
      background: 'var(--bg-card)', borderRadius: 12, padding: '14px 16px',
      border: `1px solid ${isOver ? 'rgba(239,68,68,0.3)' : 'var(--border)'}`,
      transition: 'transform 0.2s, box-shadow 0.2s',
    }}
      onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.2)'; }}
      onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>{env.icon}</span> {env.name}
        </span>
        {isOver && <span style={{ fontSize: 11, color: '#EF4444', fontWeight: 700 }}>EXCEDIDO ⚠️</span>}
        {!isOver && <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{env.utilization_pct.toFixed(0)}%</span>}
      </div>
      {/* Progress bar */}
      <div style={{ background: 'var(--bg-elevated)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, borderRadius: 4,
          background: barColor, transition: 'width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          Gasto: {fmtBRL(env.spent)}
        </span>
        <span style={{ fontSize: 12, color: isOver ? '#EF4444' : '#10B981', fontWeight: 600 }}>
          {isOver ? '−' : '+'}{fmtBRL(Math.abs(env.available))}
        </span>
      </div>
    </div>
  );
}

// ── Cash Flow Tooltip ─────────────────────────────────────────────────────────
const CashFlowTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const isProj = payload[0]?.payload?.is_projected;
  return (
    <div className="card" style={{ padding: '12px 16px', fontSize: 13, minWidth: 200 }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
        {fmtMonth(label)} {isProj && <span style={{ fontSize: 10, color: '#8B5CF6', background: 'rgba(139,92,246,0.2)', borderRadius: 4, padding: '1px 6px' }}>PROJEÇÃO</span>}
      </p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color, fontWeight: 600 }}>
          {p.name === 'income' ? '↑ Receita' : p.name === 'expenses' ? '↓ Despesas' : 'Saldo'}: {fmtBRL(p.value)}
        </p>
      ))}
    </div>
  );
};

// ── Commitment Row ────────────────────────────────────────────────────────────
function CommitmentRow({ c, onPay }) {
  const [loading, setLoading] = useState(false);

  const handlePayClick = async () => {
    setLoading(true);
    await onPay(c.id);
    setLoading(false);
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 8, flexShrink: 0, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 16,
        background: c.commitment_type === 'SUBSCRIPTION' ? 'rgba(99,102,241,0.15)' : 
                    c.commitment_type === 'INSTALLMENT' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
      }}>
        {c.commitment_type === 'SUBSCRIPTION' ? '🔄' : 
         c.commitment_type === 'INSTALLMENT' ? '📦' : '💸'}
      </div>
      <div style={{ flex: 1 }}>
        <p style={{ fontWeight: 600, fontSize: 13, margin: 0 }}>{c.label}</p>
        <p style={{ color: c.is_overdue ? '#EF4444' : 'var(--text-muted)', fontSize: 12, margin: 0 }}>
          {c.is_overdue ? '⚠️ Vencido – ' : ''}{c.due_date}
        </p>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontWeight: 700, color: '#F59E0B' }}>{fmtBRL(c.amount)}</span>
        {c.commitment_type === 'TRANSACTION' && (
          <button 
            className="btn btn-ghost" 
            onClick={handlePayClick}
            disabled={loading}
            style={{ padding: '4px 8px', fontSize: 11, height: 28, background: 'rgba(16,185,129,0.1)', color: '#10B981', borderColor: 'rgba(16,185,129,0.2)' }}
          >
            {loading ? '...' : 'Pagar'}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────
const Skel = ({ h = 14, w = '100%', r = 8 }) => (
  <div className="skeleton" style={{ height: h, width: w, borderRadius: r }} />
);

interface UpcomingCommitment {
  id: string;
  label: string;
  amount: number;
  due_date: string;
  commitment_type: 'INSTALLMENT' | 'SUBSCRIPTION' | 'TRANSACTION';
  is_overdue: boolean;
}

interface Transaction {
  id: string;
  description: string;
  amount: number;
  date: string;
  category: string;
  transaction_type: 'CREDIT' | 'DEBIT' | 'TRANSFER';
  installment_label?: string;
  funding_state?: string;
}

interface DashboardData {
  kpis: any;
  envelope_health: any[];
  cash_flow_projection: any[];
  upcoming_commitments: UpcomingCommitment[];
  recent_transactions: Transaction[];
  meta?: { period_month: string };
  _v1?: boolean;
  summary?: any;
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const d = await api.dashboard.v2();
      setData(d);
    } catch (e) {
      // Fallback to v1 if v2 not ready
      try {
        const v1 = await api.dashboard.get({ months_back: 6 });
        setData({ _v1: true, ...v1 });
      } catch (e2) {
        setError(e2.message);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const handlePay = async (id: string) => {
    try {
      await api.transactions.execute(id);
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="fade-in">
        <div className="page-header"><h1 className="page-title">Dashboard</h1></div>
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚡</div>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 8 }}>Backend não conectado</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            Inicie o servidor: <code style={{ background: 'var(--bg-elevated)', padding: '2px 8px', borderRadius: 4 }}>
              uvicorn main:app --reload
            </code>
          </p>
        </div>
      </div>
    );
  }

  // ── V1 fallback rendering ─────────────────────────────────────────────────
  if (data?._v1) {
    return (
      <div className="fade-in">
        <div className="page-header">
          <h1 className="page-title">Dashboard <span style={{ fontSize: 13, color: '#6B7280', fontWeight: 400 }}>(modo básico)</span></h1>
        </div>
        <div className="summary-grid">
          {[
            { label: 'Saldo Total', value: data.summary?.total_balance, type: 'balance' },
            { label: 'Receitas', value: data.summary?.total_income, type: 'income' },
            { label: 'Despesas', value: data.summary?.total_expenses, type: 'expense' },
          ].map(c => (
            <div key={c.label} className={`summary-card ${c.type}`}>
              <span className="summary-label">{c.label}</span>
              <span className="summary-value">{fmtBRL(c.value)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const kpis = data?.kpis || {};
  const envelopes = data?.envelope_health || [];
  const flow = data?.cash_flow_projection || [];
  const commitments = data?.upcoming_commitments || [];
  const recent = data?.recent_transactions || [];

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Dashboard Institucional</h1>
          <p className="page-subtitle">
            {data?.meta?.period_month ? `Período: ${fmtMonth(data.meta.period_month)}` : 'Carregando…'}
          </p>
        </div>
        <button onClick={load} style={{
          background: 'transparent', border: '1px solid var(--border)',
          color: 'var(--text-secondary)', borderRadius: 8, padding: '8px 14px',
          cursor: 'pointer', fontSize: 13,
        }}>
          ⟳ Atualizar
        </button>
      </div>

      {/* ── TOPO: Ready to Assign Banner ── */}
      <ReadyToAssignBanner kpi={kpis.ready_to_assign} /> {/* Removed !loading condition */}

      {/* ── 1. KPI STRIP (F-Pattern — top-left first) ── */}
      <div className="summary-grid" style={{ display: 'flex', gap: 16, marginBottom: 24, overflowX: 'auto', paddingBottom: 8 }}>
        {loading ? [1,2,3,4,5].map(i => (
          <div key={i} className="summary-card" style={{ minWidth: 200 }}>
            <Skel h={12} w="40%" />
            <div style={{ height: 8 }} />
            <Skel h={24} w="70%" />
          </div>
        )) : (
          <>
            <KPICard kpi={kpis.ready_to_assign} accent="#F59E0B" />
            <KPICard kpi={kpis.net_worth} accent={kpis.net_worth?.value >= 0 ? '#10B981' : '#EF4444'} />
            <KPICard kpi={kpis.total_income} accent="#10B981" />
            <KPICard kpi={kpis.total_expenses} accent="#F97316" />
            <KPICard kpi={kpis.savings_rate} isCurrency={false} accent="#8B5CF6" />
          </>
        )}
      </div>

      {/* ── 2. CHARTS ROW ── */}
      <div className="charts-grid" style={{ marginBottom: 24 }}>
        {/* Cash Flow Projection */}
        <div className="card" style={{ minHeight: 280 }}>
          <p className="chart-title">Fluxo de Caixa</p>
          <p className="chart-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Histórico + Projeção
            <span style={{ fontSize: 11, background: 'rgba(139,92,246,0.15)', color: '#8B5CF6', borderRadius: 4, padding: '2px 7px' }}>
              {flow.filter(f => f.is_projected).length} meses projetados {/* Updated text */}
            </span>
          </p>
          {loading ? <Skel h={220} /> : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={flow}>
                <defs>
                  <linearGradient id="gradInc" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradExp" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F59E0B" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradProj" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" tickFormatter={fmtMonth}
                  tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={v => `R$${(v / 1000).toFixed(0)}k`}
                  tick={{ fill: '#64748B', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CashFlowTooltip />} />
                <Area type="monotone" dataKey="income" stroke="#10B981" strokeWidth={2}
                  fill="url(#gradInc)" strokeDasharray={d => d?.is_projected ? '6 3' : '0'} />
                <Area type="monotone" dataKey="expenses" stroke="#F59E0B" strokeWidth={2}
                  fill="url(#gradExp)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Envelope Utilization Radial */}
        <div className="card">
          <p className="chart-title">Envelopes do Mês</p>
          <p className="chart-subtitle">Percentual utilizado por categoria</p>
          {loading ? <Skel h={220} /> : envelopes.filter(e => !e.is_system).length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 0' }}>
              <div className="empty-state-icon">📦</div>
              <p>Nenhum envelope criado. Configure o orçamento ZBB!</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <RadialBarChart
                innerRadius="20%" outerRadius="90%"
                data={envelopes.filter(e => !e.is_system).slice(0, 6).map(e => ({
                  name: e.name, value: Math.min(e.utilization_pct, 100),
                  fill: e.is_overspent ? '#EF4444' : e.color,
                }))}
                startAngle={180} endAngle={0}
              >
                <RadialBar background dataKey="value" />
                <Tooltip formatter={(v, n) => [`${v.toFixed(1)}%`, n]} />
              </RadialBarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── 3. ENVELOPE CARDS ── */}
      {!loading && envelopes.filter(e => !e.is_system).length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <p style={{ fontWeight: 700, fontSize: 15, marginBottom: 12, color: 'var(--text-primary)' }}>
            💼 Envelopes de Orçamento
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 12,
          }}>
            {envelopes.filter(e => !e.is_system).map(env => (
              <EnvelopeCard key={env.id} env={env} />
            ))}
          </div>
        </div>
      )}

      {/* ── 4. BOTTOM: Commitments + Recent Transactions ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: 16 }}>

        {/* Upcoming Commitments */}
        <div className="card">
          <p className="chart-title" style={{ marginBottom: 12 }}>
            🗓️ Compromissos (30 dias)
          </p>
          {loading ? [1,2,3].map(i => <Skel key={i} h={42} r={6} />) :
            commitments.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 0' }}>
                <div className="empty-state-icon">✅</div>
                <p>Nenhum compromisso próximo</p>
              </div>
            ) : (
              commitments.slice(0, 8).map(c => <CommitmentRow key={c.id} c={c} onPay={handlePay} />)
            )
          }
        </div>

        {/* Recent Transactions */}
        <div className="card">
          <p className="chart-title" style={{ marginBottom: 16 }}>📋 Transações Recentes</p>
          {loading ? [1,2,3].map(i => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 12, alignItems: 'center' }}>
              <Skel h={38} w={38} r="50%" />
              <div style={{ flex: 1 }}><Skel h={13} w="60%" /><div style={{ h: 4 }} /><Skel h={11} w="40%" /></div>
              <Skel h={14} w={70} />
            </div>
          )) : recent.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📭</div>
              <p>Importe um extrato para começar!</p>
            </div>
          ) : (
            <div className="txn-list">
              {recent.map(t => {
                const isCredit = t.transaction_type === 'CREDIT';
                const isUnfunded = t.funding_state === 'UNFUNDED';
                return (
                  <div key={t.id} className="txn-row">
                    <div className={`txn-icon ${isCredit ? 'credit' : 'debit'}`}>
                      {ICONS[t.category] || '💳'}
                    </div>
                    <div className="txn-info">
                      <p className="txn-description">
                        {t.description || '—'}
                        {t.installment_label && (
                          <span style={{ fontSize: 11, color: '#6366F1', marginLeft: 6 }}>
                            📦 {t.installment_label}
                          </span>
                        )}
                      </p>
                      <p className="txn-meta">
                        {t.category} · {fmtDate(t.date)}
                        {isUnfunded && <span style={{ color: '#EF4444', marginLeft: 6, fontSize: 11 }}>⚠️ Não financiado</span>}
                      </p>
                    </div>
                    <span className={`txn-amount ${isCredit ? 'credit' : 'debit'}`}>
                      {isCredit ? '+' : '−'}{fmtBRL(t.amount)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes subtlePulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(245,158,11,0.3); }
          50% { box-shadow: 0 0 16px 4px rgba(245,158,11,0.15); }
        }
      `}</style>
    </div>
  );
}
