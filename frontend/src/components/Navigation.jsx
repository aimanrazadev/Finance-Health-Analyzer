import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/Navigation.css';

const primaryLinks = [
  { label: 'Dashboard', path: '/dashboard', icon: 'D', accent: 'blue' },
  { label: 'Transactions', path: '/transactions', icon: 'T', accent: 'gray' },
  { label: 'Categories', path: '/categories', icon: 'C', accent: 'pink' },
  { label: 'Upload', path: '/upload', icon: 'U', accent: 'purple' },
  { label: 'Friends', path: '/friends', icon: 'F', accent: 'green' },
];

const intelligenceLinks = [
  { label: 'Budgets', path: '/budgets', icon: 'B', accent: 'purple' },
  { label: 'Investments', path: '/investments', icon: 'I', accent: 'green' },
  { label: 'Health', path: '/financial-health', icon: 'H', accent: 'blue' },
  { label: 'Forecast', path: '/forecast', icon: 'F', accent: 'orange' },
  { label: 'Subscriptions', path: '/subscriptions', icon: 'S', accent: 'pink' },
  { label: 'Insights', path: '/insights', icon: 'AI', accent: 'orange' },
];

const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="app-sidebar">
      <Link to="/" className="navbar-brand">
        <span className="brand-mark">F</span>
        <span>FinSight AI</span>
      </Link>

      <nav className="sidebar-nav" aria-label="Main navigation">
        <span className="nav-section-label">Workspace</span>
        {primaryLinks.map((item) => (
          <NavLink to={item.path} className={`nav-link accent-${item.accent}`} key={item.path}>
            <span className="nav-icon" aria-hidden>{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}

        <span className="nav-section-label">Intelligence</span>
        {intelligenceLinks.map((item) => (
          <NavLink to={item.path} className={`nav-link accent-${item.accent}`} key={item.path}>
            <span className="nav-icon" aria-hidden>{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="nav-user">
        <span className="user-email">{user?.email}</span>
        <button onClick={handleLogout} className="logout-button">
          Logout
        </button>
      </div>
    </aside>
  );
};

export default Navigation;
