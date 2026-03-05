import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Accounts from './pages/Accounts';
import Import from './pages/Import';

function Sidebar() {
  const navItems = [
    { to: '/',             icon: '📊', label: 'Dashboard'   },
    { to: '/transactions', icon: '💸', label: 'Transações'  },
    { to: '/accounts',     icon: '💳', label: 'Contas & Cartões' },
    { to: '/import',       icon: '📂', label: 'Importar'    },
  ];

  return (
    <aside className="sidebar">
      <a href="/" className="logo">
        <div className="logo-icon">💰</div>
        <span className="logo-text">FinanceApp</span>
      </a>

      <span className="nav-section-label">Menu</span>

      {navItems.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <span className="nav-icon">{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}

      <div style={{ marginTop: 'auto', paddingTop: '2rem' }}>
        <UserSwitcher />
      </div>
    </aside>
  );
}

import { useState, useEffect } from 'react';
import { api } from './services/api';

function UserSwitcher() {
  const [users, setUsers] = useState<any[]>([]);
  const [activeId, setActiveId] = useState(localStorage.getItem('activeUserId') || 'demo-user');
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');

  const loadUsers = async () => {
    try {
      const list = await api.users.list();
      setUsers(list);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleSwitch = (id: string) => {
    localStorage.setItem('activeUserId', id);
    setActiveId(id);
    window.location.reload(); // Reload to refresh all data with new user
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const newUser = await api.users.create({ name: newName, email: newEmail });
      await loadUsers();
      handleSwitch(newUser.id);
    } catch (err) {
      alert('Erro ao criar usuário');
    }
  };

  return (
    <div className="user-switcher">
      <span className="nav-section-label">Usuário Ativo</span>
      <select 
        value={activeId} 
        onChange={(e) => handleSwitch(e.target.value)}
        className="user-select"
        style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-color)' }}
      >
        {users.map(u => (
          <option key={u.id} value={u.id}>{u.name}</option>
        ))}
        {!users.find(u => u.id === 'demo-user') && <option value="demo-user">Demo User</option>}
      </select>

      <button 
        onClick={() => setShowAdd(!showAdd)}
        style={{ background: 'none', border: 'none', color: 'var(--accent-color)', cursor: 'pointer', fontSize: '0.8rem', marginTop: '0.5rem' }}
      >
        + Novo Usuário
      </button>

      {showAdd && (
        <form onSubmit={handleAddUser} style={{ marginTop: '0.5rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <input 
            placeholder="Nome" 
            value={newName} 
            onChange={e => setNewName(e.target.value)} 
            required
            style={{ padding: '0.3rem', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-app)', color: 'white' }}
          />
          <input 
            placeholder="Email" 
            value={newEmail} 
            onChange={e => setNewEmail(e.target.value)} 
            type="email" 
            required
            style={{ padding: '0.3rem', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-app)', color: 'white' }}
          />
          <button type="submit" className="btn-primary" style={{ padding: '0.3rem' }}>Criar</button>
        </form>
      )}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/"             element={<Dashboard />}    />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/accounts"     element={<Accounts />}     />
            <Route path="/import"       element={<Import />}       />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
