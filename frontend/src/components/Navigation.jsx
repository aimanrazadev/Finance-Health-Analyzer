import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/Navigation.css';

const iconPaths = {
  brand: [
    <path key="brand-1" d="M3 12h3l2-5 4 10 3-7 2 2h4" />,
  ],
  dashboard: [
    <rect key="dashboard-1" x="3" y="3" width="7" height="7" rx="1.5" />,
    <rect key="dashboard-2" x="14" y="3" width="7" height="7" rx="1.5" />,
    <rect key="dashboard-3" x="14" y="14" width="7" height="7" rx="1.5" />,
    <rect key="dashboard-4" x="3" y="14" width="7" height="7" rx="1.5" />,
  ],
  transactions: [
    <path key="transactions-1" d="M4 7h16" />,
    <path key="transactions-2" d="M4 12h16" />,
    <path key="transactions-3" d="M4 17h16" />,
  ],
  categories: [
    <path key="categories-1" d="M6 4h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z" />,
    <path key="categories-2" d="M9 9h6" />,
    <path key="categories-3" d="M9 15h6" />,
  ],
  friends: [
    <path key="friends-1" d="M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" />,
    <circle key="friends-2" cx="9.5" cy="7" r="4" />,
    <path key="friends-3" d="M22 21v-2a4 4 0 0 0-3-3.87" />,
    <path key="friends-4" d="M16 3.13a4 4 0 0 1 0 7.75" />,
  ],
  advisor: [
    <path key="advisor-1" d="M12 3l1.7 5.1L19 10l-5.3 1.9L12 17l-1.7-5.1L5 10l5.3-1.9L12 3Z" />,
    <path key="advisor-2" d="M5 4v3" />,
    <path key="advisor-3" d="M3.5 5.5h3" />,
    <path key="advisor-4" d="M19 17v3" />,
    <path key="advisor-5" d="M17.5 18.5h3" />,
  ],
};

const NavIcon = ({ name, className = 'nav-lucide-icon' }) => (
  <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
    {iconPaths[name]}
  </svg>
);

const UploadIcon = () => (
  <svg className="nav-lucide-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M17 8 12 3 7 8" />
    <path d="M12 3v12" />
  </svg>
);

const LogoutIcon = () => (
  <svg className="nav-lucide-icon" viewBox="0 0 24 24" aria-hidden="true">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <path d="m16 17 5-5-5-5" />
    <path d="M21 12H9" />
  </svg>
);

const primaryLinks = [
  { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
  { label: 'Transactions', path: '/transactions', icon: 'transactions' },
  { label: 'Categories', path: '/categories', icon: 'categories' },
  { label: 'Friends', path: '/friends', icon: 'friends' },
  { label: 'AI Advisor', path: '/ai-advisor', icon: 'advisor' },
];

const Navigation = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="app-sidebar">
      <Link to="/" className="navbar-brand">
        <span className="brand-mark"><NavIcon name="brand" /></span>
        <span className="brand-copy">
          <strong>Finance Health <em>AI</em></strong>
          <small>Analyzer</small>
        </span>
      </Link>

      <nav className="sidebar-nav" aria-label="Main navigation">
        <span className="nav-section-label">Finance Health Analyzer</span>
        {primaryLinks.map((item) => (
          <NavLink to={item.path} className="nav-link" key={item.path}>
            <span className="nav-icon" aria-hidden="true">
              <NavIcon name={item.icon} />
            </span>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
        <NavLink to="/upload" className="nav-link mobile-upload-link">
          <span className="nav-icon" aria-hidden="true">
            <UploadIcon />
          </span>
          <span className="nav-label">Upload Statement</span>
        </NavLink>
      </nav>

      <div className="nav-user">
        <NavLink to="/upload" className="nav-bottom-button upload-bottom-link">
          <UploadIcon />
          <span>Upload Statement</span>
        </NavLink>
        <button onClick={handleLogout} className="logout-button">
          <LogoutIcon />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
};

export default Navigation;
