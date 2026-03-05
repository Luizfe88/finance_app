import { useEffect, useState } from 'react';
import { 
  Plus, 
  CreditCard, 
  Wallet, 
  Trash2, 
  Edit2, 
  ChevronRight, 
  Check, 
  X,
  Building2,
  DollarSign
} from 'lucide-react';
import { api, Account } from '../services/api';

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [form, setForm] = useState({
    bank_name: '',
    account_type: 'CHECKING',
    balance: '',
    invoice_due_day: '',
    invoice_closing_day: '',
    masked_account_number: '****'
  });

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.accounts.list();
      setAccounts(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSave = async (id?: string) => {
    console.log('handleSave called', { id, form });
    setError(null);
    try {
      const balanceValue = form.balance.toString().trim();
      const parsedBalance = balanceValue ? parseFloat(balanceValue.replace(',', '.')) : 0;
      
      if (isNaN(parsedBalance)) {
        throw new Error('Valor de saldo inválido');
      }

      const payload: any = {
        bank_name: form.bank_name,
        account_type: form.account_type,
        balance: parsedBalance,
        invoice_due_day: (form.invoice_due_day && !isNaN(parseInt(form.invoice_due_day))) ? parseInt(form.invoice_due_day) : null,
        invoice_closing_day: (form.invoice_closing_day && !isNaN(parseInt(form.invoice_closing_day))) ? parseInt(form.invoice_closing_day) : null,
        masked_account_number: form.masked_account_number || "****"
      };

      console.log('Sending payload:', payload);

      if (id) {
        await api.accounts.update(id, payload);
      } else {
        await api.accounts.create(payload);
      }

      console.log('Save successful');
      setEditingId(null);
      setShowAddForm(false);
      load();
      resetForm();
    } catch (e: any) {
      console.error('Save error:', e);
      setError(e.message || 'Erro ao salvar conta');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Excluir esta conta?')) return;
    try {
      await api.accounts.delete(id);
      load();
    } catch (e) {
      console.error(e);
    }
  };

  const resetForm = () => {
    setForm({
      bank_name: '',
      account_type: 'CHECKING',
      balance: '',
      invoice_due_day: '',
      invoice_closing_day: '',
      masked_account_number: '****'
    });
    setError(null);
  };

  const startEdit = (acc: Account) => {
    setForm({
      bank_name: acc.bank_name,
      account_type: acc.account_type,
      balance: acc.balance.toString(),
      invoice_due_day: acc.invoice_due_day?.toString() || '',
      invoice_closing_day: acc.invoice_closing_day?.toString() || '',
      masked_account_number: acc.masked_account_number
    });
    setEditingId(acc.id);
    setShowAddForm(false);
  };

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Contas & Cartões</h1>
          <p className="page-subtitle">Gerencie suas fontes de recursos e limites de crédito</p>
        </div>
        <button 
          className="btn btn-primary" 
          onClick={() => { setShowAddForm(!showAddForm); setEditingId(null); resetForm(); }}
        >
          <Plus size={18} />
          {showAddForm ? 'Cancelar' : 'Nova Conta'}
        </button>
      </div>

      {showAddForm && (
        <div className="card fade-in" style={{ marginBottom: 32, border: '1px solid var(--color-primary)' }}>
          <h3 style={{ marginBottom: 20 }}>Adicionar Nova Conta</h3>
          <AccountFormLayout 
            form={form} 
            setForm={setForm} 
            onSave={() => handleSave()} 
            onCancel={() => setShowAddForm(false)}
            error={error}
          />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 24 }}>
        {accounts.map(acc => {
          const isEditing = editingId === acc.id;
          const isCard = acc.account_type === 'CREDIT_CARD';
          
          return (
            <div key={acc.id} className={`card ${isEditing ? 'editing' : ''}`} style={{ 
              position: 'relative',
              borderColor: isEditing ? 'var(--color-primary)' : 'var(--border-subtle)'
            }}>
              {isEditing ? (
                <AccountFormLayout 
                  form={form} 
                  setForm={setForm} 
                  onSave={() => handleSave(acc.id)} 
                  onCancel={() => setEditingId(null)}
                  error={error}
                />
              ) : (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
                    <div style={{ 
                      width: 48, height: 48, borderRadius: 12, 
                      background: isCard ? 'rgba(99,102,241,0.1)' : 'rgba(16,185,129,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      {isCard ? <CreditCard size={24} color="var(--color-primary)" /> : <Building2 size={24} color="var(--color-income)" />}
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-ghost" style={{ padding: 8 }} onClick={() => startEdit(acc)}>
                        <Edit2 size={16} />
                      </button>
                      <button className="btn btn-ghost" style={{ padding: 8 }} onClick={() => handleDelete(acc.id)}>
                        <Trash2 size={16} color="var(--color-danger)" />
                      </button>
                    </div>
                  </div>

                  <div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{acc.bank_name}</h3>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                      {isCard ? 'CARTÃO DE CRÉDITO' : 'CONTA CORRENTE'} • {acc.masked_account_number}
                    </p>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>Saldo Atual</span>
                      <span style={{ fontSize: 22, fontWeight: 800 }}>
                        {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(acc.balance)}
                      </span>
                    </div>

                    {isCard && acc.invoice_due_day && (
                      <div style={{ 
                        marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border-subtle)',
                        display: 'flex', gap: 16, fontSize: 12
                      }}>
                        <div>
                          <p style={{ color: 'var(--text-muted)' }}>Fatura vence dia</p>
                          <p style={{ fontWeight: 700 }}>{acc.invoice_due_day}</p>
                        </div>
                        <div>
                          <p style={{ color: 'var(--text-muted)' }}>Fecha dia</p>
                          <p style={{ fontWeight: 700 }}>{acc.invoice_closing_day}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AccountFormLayout({ form, setForm, onSave, onCancel, error }: any) {
  const isCard = form.account_type === 'CREDIT_CARD';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="form-group">
        <label className="form-label">Instituição Financeira</label>
        <input 
          className="input" 
          value={form.bank_name} 
          onChange={e => setForm({...form, bank_name: e.target.value})}
          placeholder="Ex: Nubank, Itaú, Inter..."
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Tipo</label>
          <select 
            className="input" 
            value={form.account_type} 
            onChange={e => setForm({...form, account_type: e.target.value})}
          >
            <option value="CHECKING">Conta Corrente / Dinheiro</option>
            <option value="CREDIT_CARD">Cartão de Crédito</option>
            <option value="SAVINGS">Reserva de Emergência</option>
            <option value="INVESTMENT">Investimentos</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Saldo Inicial / Limite</label>
          <input 
            className="input" 
            value={form.balance} 
            onChange={e => setForm({...form, balance: e.target.value})}
            placeholder="0,00"
          />
        </div>
      </div>

      {isCard && (
        <div className="form-row fade-in">
          <div className="form-group">
            <label className="form-label">Dia de Fechamento</label>
            <input 
              className="input" 
              type="number" min="1" max="31"
              value={form.invoice_closing_day} 
              onChange={e => setForm({...form, invoice_closing_day: e.target.value})}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Dia de Vencimento</label>
            <input 
              className="input" 
              type="number" min="1" max="31"
              value={form.invoice_due_day} 
              onChange={e => setForm({...form, invoice_due_day: e.target.value})}
            />
          </div>
        </div>
      )}

      {error && <p style={{ color: 'var(--color-danger)', fontSize: 13 }}>{error}</p>}

      <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
        <button className="btn btn-ghost" style={{ flex: 1 }} onClick={onCancel}>Cancelar</button>
        <button className="btn btn-primary" style={{ flex: 1 }} onClick={onSave}>
          <Check size={18} />
          Salvar
        </button>
      </div>
    </div>
  );
}
