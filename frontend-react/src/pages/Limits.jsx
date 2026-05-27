import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { formatCurrency } from '../utils/format';

function Limits() {
  const [caps, setCaps] = useState({});
  const [currentSpends, setCurrentSpends] = useState({});
  const [catInput, setCatInput] = useState('Food');
  const [amtInput, setAmtInput] = useState('');
  const [alert, setAlert] = useState(null);

  const fetchData = async () => {
    try {
      const [capsRes, sumRes] = await Promise.all([
        apiClient.get('/caps'),
        apiClient.get('/summary')
      ]);
      setCaps(capsRes.data.caps || {});
      
      const spends = {};
      if (sumRes.data.by_category) {
        Object.entries(sumRes.data.by_category).forEach(([cat, val]) => {
          if (val.total < 0) {
            spends[cat] = Math.abs(val.total);
          }
        });
      }
      setCurrentSpends(spends);
      
      // Check for alerts
      for (const [cat, limit] of Object.entries(capsRes.data.caps || {})) {
        const spent = spends[cat] || 0;
        if (spent > limit) {
          setAlert({ cat, limit, spent });
          break; // Show one alert at a time
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveCap = async () => {
    if (!catInput || !amtInput) return;
    try {
      await apiClient.post('/caps', { category: catInput, amount: parseFloat(amtInput) });
      setAmtInput('');
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteCap = async (cat) => {
    if (!window.confirm(`Delete budget cap for ${cat}?`)) return;
    try {
      await apiClient.delete(`/caps/${cat}`);
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Delete failed');
    }
  };

  const handleEditCap = (cat, limit) => {
    setCatInput(cat);
    setAmtInput(limit);
  };

  return (
    <div>
      {alert && (
        <div className="alert-banner" style={{
          background: '#fef2f2', border: '1px solid #fecaca', borderLeft: '4px solid var(--error)',
          padding: '1rem', borderRadius: '8px', display: 'flex', gap: '1rem', alignItems: 'flex-start',
          marginBottom: '1rem', color: '#991b1b'
        }}>
          <i className="fa-solid fa-triangle-exclamation" style={{fontSize: '1.5rem'}}></i>
          <div>
            <strong style={{display:'block', marginBottom: '0.2rem'}}>Budget Limit Exceeded!</strong>
            <span>You have exceeded your {formatCurrency(alert.limit)} limit for {alert.cat}. Current spend is {formatCurrency(alert.spent)}.</span>
          </div>
        </div>
      )}

      <div className="card">
        <h3 style={{marginTop:0}}><i className="fa-solid fa-shield-halved" style={{color:'var(--primary)'}}></i> Set Category Budget Caps</h3>
        <p style={{color:'var(--text-muted)', fontSize:'0.9rem', marginBottom: '1.5rem'}}>Set spending limits to receive real-time alerts.</p>
        
        <div style={{display:'flex', gap: '1rem', alignItems:'flex-end'}}>
          <div style={{flex: 1}}>
            <label style={{display:'block', fontSize:'0.85rem', fontWeight:600, marginBottom:'0.5rem'}}>Category</label>
            <select style={{width: '100%'}} value={catInput} onChange={e => setCatInput(e.target.value)}>
              <option value="Food">Food</option>
              <option value="Transport">Transport</option>
              <option value="Shopping">Shopping</option>
              <option value="Subscriptions">Subscriptions</option>
              <option value="Entertainment">Entertainment</option>
              <option value="Housing">Housing</option>
            </select>
          </div>
          <div style={{flex: 1}}>
            <label style={{display:'block', fontSize:'0.85rem', fontWeight:600, marginBottom:'0.5rem'}}>Monthly Cap (đ)</label>
            <input type="number" placeholder="e.g. 500" style={{width:'100%'}} value={amtInput} onChange={e => setAmtInput(e.target.value)} />
          </div>
          <button className="btn-primary" onClick={handleSaveCap}>Save Cap</button>
        </div>

        <h4 style={{marginTop: '2rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem'}}>Active Caps</h4>
        <table className="txn-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Monthly Limit</th>
              <th>Current Spend</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {Object.keys(caps).length === 0 ? (
              <tr><td colSpan="5" style={{textAlign:'center', color: 'var(--text-muted)'}}>No limits set.</td></tr>
            ) : (
              Object.entries(caps).map(([cat, limit]) => {
                const spent = currentSpends[cat] || 0;
                const isOver = spent > limit;
                return (
                  <tr key={cat}>
                    <td style={{fontWeight:500}}>{cat}</td>
                    <td>{formatCurrency(limit)}</td>
                    <td style={{color: isOver ? 'var(--error)' : 'var(--text-main)'}}>{formatCurrency(spent)}</td>
                    <td>
                      {isOver 
                        ? <span style={{background:'#fee2e2', color:'#991b1b', padding:'2px 8px', borderRadius:'12px', fontSize:'0.8rem', fontWeight:600}}>Exceeded</span>
                        : <span style={{background:'#dcfce7', color:'#166534', padding:'2px 8px', borderRadius:'12px', fontSize:'0.8rem', fontWeight:600}}>On Track</span>
                      }
                    </td>
                    <td>
                      <button onClick={() => handleEditCap(cat, limit)} style={{background:'transparent', border:'none', color:'var(--primary)', cursor:'pointer', marginRight:'0.5rem'}} title="Edit">
                        <i className="fa-solid fa-pen-to-square"></i>
                      </button>
                      <button onClick={() => handleDeleteCap(cat)} style={{background:'transparent', border:'none', color:'var(--error)', cursor:'pointer'}} title="Delete">
                        <i className="fa-solid fa-trash"></i>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Limits;
