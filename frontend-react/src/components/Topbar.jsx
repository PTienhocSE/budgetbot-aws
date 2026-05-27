import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import apiClient from '../api/client';
import './Topbar.css';

function Topbar() {
  const [status, setStatus] = useState('checking');
  const location = useLocation();

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await apiClient.get('/health');
        setStatus('online');
      } catch (err) {
        setStatus('offline');
      }
    };
    checkHealth();
  }, []);

  const titles = {
    '/overview': 'Overview',
    '/chat': 'AI Money Assistant',
    '/coach': 'Budget Coach',
    '/limits': 'Caps & Alerts'
  };

  const title = titles[location.pathname] || 'BudgetBot';

  return (
    <header className="topbar">
      <h1>{title}</h1>
      <div className="status-pills">
        {status === 'checking' && <><span className="spinner"></span> Checking API...</>}
        {status === 'online' && <span style={{color: 'var(--success)'}}><i className="fa-solid fa-circle-check"></i> API Connected</span>}
        {status === 'offline' && <span style={{color: 'var(--error)'}}><i className="fa-solid fa-circle-xmark"></i> Backend Offline</span>}
      </div>
    </header>
  );
}

export default Topbar;
