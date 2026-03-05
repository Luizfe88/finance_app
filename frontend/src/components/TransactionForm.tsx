import React, { useState, useEffect } from 'react';
import { 
  ArrowUpCircle, 
  ArrowDownCircle, 
  Tag, 
  CreditCard, 
  Wallet, 
  RefreshCcw, 
  X,
  Check,
  Plus
} from 'lucide-react';
import { api } from '../services/api';

interface Account {
  id: string;
  bank_name: string;
  account_type: string;
  invoice_due_day?: number;
  invoice_closing_day?: number;
}

interface TransactionFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

const CATEGORIES = [
  'Alimentação', 'Transporte', 'Moradia', 'Saúde',
  'Educação', 'Lazer', 'Roupas', 'Serviços', 'Outros'
];

const PAYMENT_METHODS = [
  { id: 'CASH_PIX', label: 'Dinheiro / Pix', icon: <Wallet size={16} /> },
  { id: 'DEBIT_CARD', label: 'Cartão de Débito', icon: <CreditCard size={16} /> },
  { id: 'CREDIT_CARD', label: 'Cartão de Crédito', icon: <CreditCard size={16} color="#818CF8" /> },
  { id: 'BOLETO_TRANSFER', label: 'Boleto / Transferência', icon: <Plus size={16} /> },
  { id: 'OTHER', label: 'Outros', icon: <Tag size={16} /> },
];

export default function TransactionForm({ onSuccess, onCancel }: TransactionFormProps) {
  const [type, setType] = useState<'DEBIT' | 'CREDIT' | 'TRANSFER'>('DEBIT');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [category, setCategory] = useState('Outros');
  const [accountId, setAccountId] = useState('');
  const [toAccountId, setToAccountId] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('CASH_PIX');
  const [installmentCount, setInstallmentCount] = useState(1);
  const [isRecurring, setIsRecurring] = useState(false);
  const [isPaid, setIsPaid] = useState(true);
  const [memo, setMemo] = useState('');
  
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadAccounts = async () => {
      try {
        const res = await api.accounts.list();
        setAccounts(res);
        if (res.length > 0) {
          setAccountId(res[0].id);
          if (res.length > 1) setToAccountId(res[1].id);
          else setToAccountId(res[0].id);
        }
      } catch (e) {
        console.error('Failed to load accounts', e);
      }
    };
    loadAccounts();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (type === 'TRANSFER') {
        await api.transactions.transfer({
          from_account_id: accountId,
          to_account_id: toAccountId,
          amount: parseFloat(amount.replace(',', '.')),
          description: description || 'Transferência',
          category,
          date: new Date(date).toISOString(),
          memo: memo || undefined,
        });
      } else {
        await api.transactions.create({
          account_id: accountId,
          amount: parseFloat(amount.replace(',', '.')),
          description,
          category,
          date: new Date(date).toISOString(),
          transaction_type: type,
          payment_method: paymentMethod,
          installment_count: paymentMethod === 'CREDIT_CARD' ? installmentCount : 1,
          is_recurring: isRecurring,
          is_paid: isPaid,
          memo: memo || undefined,
        });
      }
      onSuccess();
    } catch (e: any) {
      setError(e.message || 'Erro ao salvar transação');
    } finally {
      setLoading(false);
    }
  };

  const isCreditCard = paymentMethod === 'CREDIT_CARD';

  return (
    <div className="card fade-in" style={{ maxWidth: 680, margin: '0 auto', padding: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 28 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700 }}>Solicitar Lançamento</h2>
        <button className="btn btn-ghost" onClick={onCancel} style={{ padding: 10 }}>
          <X size={24} />
        </button>
      </div>

      <div className="txn-type-tabs" style={{ marginBottom: 32 }}>
        <button 
          className={`type-tab ${type === 'DEBIT' ? 'active expense' : ''}`}
          onClick={() => setType('DEBIT')}
          style={{ height: 48 }}
        >
          <ArrowDownCircle size={20} />
          Despesa
        </button>
        <button 
          className={`type-tab ${type === 'CREDIT' ? 'active income' : ''}`}
          onClick={() => setType('CREDIT')}
          style={{ height: 48 }}
        >
          <ArrowUpCircle size={20} />
          Receita
        </button>
        <button 
          className={`type-tab ${type === 'TRANSFER' ? 'active alert' : ''}`}
          onClick={() => setType('TRANSFER')}
          style={{ height: 48 }}
        >
          <Plus size={20} style={{ transform: 'rotate(45deg)' }} />
          Transferência
        </button>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <div className="form-group">
          <label className="form-label">Descrição da Transação</label>
          <input 
            className="input" 
            placeholder="O que você comprou ou recebeu?"
            value={description}
            onChange={e => setDescription(e.target.value)}
            required
            style={{ fontSize: 16, padding: '14px 16px' }}
          />
        </div>

        <div className="form-row" style={{ gridTemplateColumns: type === 'TRANSFER' ? '1fr' : '1.2fr 1fr' }}>
          <div className="form-group">
            <label className="form-label">{type === 'TRANSFER' ? 'Valor da Transferência' : 'Valor do Lançamento'}</label>
            <input 
              className="input" 
              type="text"
              placeholder="0,00"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              required
              style={{ 
                fontSize: 22, 
                fontWeight: 800, 
                color: type === 'DEBIT' ? 'var(--color-danger)' : type === 'CREDIT' ? 'var(--color-income)' : 'var(--color-primary)',
                padding: '12px 16px'
              }}
            />
          </div>
          {type !== 'TRANSFER' && (
            <div className="form-group">
              <label className="form-label">Data de Competência</label>
              <input 
                className="input" 
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                required
                style={{ padding: '12px 16px' }}
              />
            </div>
          )}
        </div>

        {type === 'TRANSFER' && (
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Data da Transferência</label>
              <input 
                className="input" 
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                required
                style={{ padding: '12px 16px' }}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Categoria</label>
              <select className="input" value={category} onChange={e => setCategory(e.target.value)} style={{ height: 48 }}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
        )}

        <div className="form-row">
          {type !== 'TRANSFER' && (
            <div className="form-group">
              <label className="form-label">Categoria Principal</label>
              <select className="input" value={category} onChange={e => setCategory(e.target.value)} style={{ height: 48 }}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          )}
          <div className="form-group">
            <label className="form-label">{type === 'TRANSFER' ? 'Conta de Origem' : 'Conta de Origem/Destino'}</label>
            <select className="input" value={accountId} onChange={e => setAccountId(e.target.value)} style={{ height: 48 }}>
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>
                  {acc.bank_name} ({acc.account_type === 'CREDIT_CARD' ? 'Cartão' : 'Conta'})
                </option>
              ))}
            </select>
          </div>
          {type === 'TRANSFER' && (
            <div className="form-group">
              <label className="form-label">Conta de Destino</label>
              <select className="input" value={toAccountId} onChange={e => setToAccountId(e.target.value)} style={{ height: 48 }}>
                {accounts.map(acc => (
                  <option key={acc.id} value={acc.id}>
                    {acc.bank_name} ({acc.account_type === 'CREDIT_CARD' ? 'Cartão' : 'Conta'})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {type !== 'TRANSFER' && (
          <div className="form-group">
            <label className="form-label">Forma de Pagamento Disponível</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
              {PAYMENT_METHODS.map(m => (
                <button
                  key={m.id}
                  type="button"
                  className={`btn btn-ghost ${paymentMethod === m.id ? 'active' : ''}`}
                  style={{ 
                    fontSize: 13, 
                    height: 44,
                    padding: '0 12px',
                    borderColor: paymentMethod === m.id ? 'var(--color-primary)' : 'var(--border-subtle)',
                    background: paymentMethod === m.id ? 'rgba(99,102,241,0.1)' : 'transparent',
                    color: paymentMethod === m.id ? 'var(--text-primary)' : 'var(--text-secondary)'
                  }}
                  onClick={() => setPaymentMethod(m.id)}
                >
                  {m.icon}
                  {m.label.split(' / ')[0]}
                </button>
              ))}
            </div>
          </div>
        )}

        {isCreditCard && type === 'DEBIT' && (
          <div className="form-group fade-in" style={{ background: 'rgba(99,102,241,0.03)', padding: 16, borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <label className="form-label" style={{ marginBottom: 12 }}>Plano de Parcelamento (1x até 36x)</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <input 
                type="range" 
                min="1" max="36" 
                style={{ flex: 1, height: 6, cursor: 'pointer' }}
                value={installmentCount}
                onChange={e => setInstallmentCount(parseInt(e.target.value))}
              />
              <div style={{ textAlign: 'right', minWidth: 100 }}>
                <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-primary)' }}>{installmentCount}x</span>
              </div>
            </div>
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
              <span>Total: R$ {amount || '0,00'}</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                Parcela: {(parseFloat(amount.replace(',', '.') || '0') / installmentCount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
              </span>
            </div>
          </div>
        )}

        {type !== 'TRANSFER' && (
          <div className="switch-group" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(99,102,241,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Check size={16} color="var(--color-primary)" />
              </div>
              <div>
                <p style={{ fontSize: 14, fontWeight: 600 }}>Já foi paga?</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Desmarque para agendar no futuro</p>
              </div>
            </div>
            <label className="switch">
              <input type="checkbox" checked={isPaid} onChange={e => setIsPaid(e.target.checked)} />
              <span className="slider"></span>
            </label>
          </div>
        )}

        {type !== 'TRANSFER' && (
          <div className="switch-group" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(99,102,241,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <RefreshCcw size={16} color="var(--color-primary)" />
              </div>
              <div>
                <p style={{ fontSize: 14, fontWeight: 600 }}>Transação Recorrente</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>Repetir este lançamento todo mês</p>
              </div>
            </div>
            <label className="switch">
              <input type="checkbox" checked={isRecurring} onChange={e => setIsRecurring(e.target.checked)} />
              <span className="slider"></span>
            </label>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Notas Complementares</label>
          <textarea 
            className="input" 
            placeholder="Algum detalhe importante sobre este gasto ou ganho?"
            style={{ height: 100, resize: 'none', padding: '12px 16px' }}
            value={memo}
            onChange={e => setMemo(e.target.value)}
          />
        </div>

        {error && (
          <div style={{ padding: 12, borderRadius: 8, background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--color-danger)' }}>
            <p style={{ color: 'var(--color-danger)', fontSize: 13, fontWeight: 500 }}>{error}</p>
          </div>
        )}

        <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
          <button type="button" className="btn btn-ghost" style={{ flex: 1, height: 52 }} onClick={onCancel}>
            Descartar
          </button>
          <button type="submit" className="btn btn-primary" style={{ flex: 2, height: 52, fontSize: 16 }} disabled={loading}>
            {loading ? 'Processando...' : (
              <>
                <Check size={20} />
                Confirmar {type === 'DEBIT' ? 'Despesa' : type === 'CREDIT' ? 'Receita' : 'Transferência'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

