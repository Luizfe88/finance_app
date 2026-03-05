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
    </aside>
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
