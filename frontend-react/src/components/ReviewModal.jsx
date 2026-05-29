import React, { useState } from 'react';
import { useUpload } from '../context/UploadContext';
import apiClient from '../api/client';
import { formatCurrency } from '../utils/format';
import { useNavigate } from 'react-router-dom';

function ReviewModal() {
  const { reviewTransactions, setReviewTransactions, triggerRefresh } = useUpload();
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();

  if (!reviewTransactions || reviewTransactions.length === 0) return null;

  const handleReviewCategoryChange = (index, newCat) => {
    const updated = [...reviewTransactions];
    updated[index].category = newCat;
    setReviewTransactions(updated);
  };

  const handleReviewSave = async () => {
    setSaving(true);
    setErrorMsg('');
    try {
      // Strip out the internal jobId field before sending payload to the API
      const cleanTxns = reviewTransactions.map(({ jobId, ...rest }) => rest);
      await apiClient.post('/transactions/batch', { transactions: cleanTxns });
      setReviewTransactions([]);
      
      if (typeof triggerRefresh === 'function') {
        triggerRefresh();
      }
      navigate('/transactions', { replace: true });
    } catch (err) {
      setErrorMsg('Batch save failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      animation: 'fadeIn 0.2s ease'
    }}>
      <div className="card" style={{ width: '90%', maxWidth: '700px', maxHeight: '80vh', overflowY: 'auto', background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
        <h3 style={{marginTop: 0, color: 'var(--error)'}}>
          <i className="fa-solid fa-triangle-exclamation"></i> Manual Review Required
        </h3>
        <p style={{color: 'var(--text-muted)'}}>
          The AI was not confident about the following {reviewTransactions.length} transaction(s). 
          Please confirm or update their categories before saving.
        </p>
        
        {errorMsg && (
          <div style={{marginBottom: '1rem', padding: '0.8rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)'}}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
          {reviewTransactions.map((txn, i) => (
            <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 150px', gap: '1rem', background: 'rgba(255,255,255,0.5)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.1)', alignItems: 'center' }}>
              <div>
                <div style={{fontWeight: 'bold'}}>{txn.description}</div>
                <div style={{fontSize: '0.85rem', color: 'var(--text-muted)'}}>{txn.date}</div>
              </div>
              <div style={{fontWeight: 'bold', color: txn.amount >= 0 ? 'var(--success)' : 'var(--error)'}}>
                {txn.amount >= 0 ? '+' : ''}{formatCurrency(Math.abs(txn.amount))}
              </div>
              <select 
                value={txn.category} 
                onChange={(e) => handleReviewCategoryChange(i, e.target.value)}
                style={{ padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
              >
                {['Food', 'Transport', 'Shopping', 'Utilities', 'Entertainment', 'Health', 'Subscriptions', 'Income', 'Transfer', 'Other'].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
          <button className="btn-outline" onClick={() => setReviewTransactions([])} style={{ borderColor: '#94a3b8', color: '#64748b' }} disabled={saving}>Cancel All</button>
          <button style={{marginTop:'0'}} className="btn-primary" onClick={handleReviewSave} disabled={saving}>
            {saving ? 'Saving...' : 'Confirm & Save All'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReviewModal;
