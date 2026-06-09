import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/Navigation.css';

const Navigation = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          <span className="brand-mark">F</span>
          <span>FinSight AI</span>
        </Link>

        <div className="navbar-menu">
          <NavLink to="/dashboard" className="nav-link">Dashboard</NavLink>
          <NavLink to="/transactions" className="nav-link">Transactions</NavLink>
          <NavLink to="/friends" className="nav-link">Friends</NavLink>
          <NavLink to="/needs-review" className="nav-link">Needs Review</NavLink>
          <NavLink to="/upload" className="nav-link">Upload</NavLink>
          <NavLink to="/budgets" className="nav-link">Budgets</NavLink>
          <NavLink to="/recommendations" className="nav-link">Recommendations</NavLink>
          <NavLink to="/savings-goals" className="nav-link">Goals</NavLink>
          <NavLink to="/insights" className="nav-link">Insights</NavLink>

          <div className="nav-user">
            <span className="user-email">{user?.email}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
