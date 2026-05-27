import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import './Navbar.css';

export default function Navbar() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Link to="/transactions">💰 BudgetBot</Link>
      </div>
      <div className="navbar-links">
        <Link to="/transactions" className="nav-link">Transactions</Link>
        <Link to="/chat" className="nav-link">AI Chat</Link>
      </div>
      <div className="navbar-user">
        <span className="user-greeting">Hi, {user?.full_name || user?.username}</span>
        <button onClick={handleLogout} className="btn-logout">Logout</button>
      </div>
    </nav>
  );
}
