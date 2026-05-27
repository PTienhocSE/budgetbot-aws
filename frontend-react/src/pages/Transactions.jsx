import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { formatCurrency } from '../utils/format';

function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [month, setMonth] = useState('');
  const [editingTxn, setEditingTxn] = useState(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Sorting state
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'desc' });

  // Add Transaction state
  const [addingTxn, setAddingTxn] = useState(false);
  const [newTxn, setNewTxn] = useState({ date: new Date().toISOString().split('T')[0], description: '', amount: '', type: 'out' });

  const refreshTransactions = async () => {
    setLoading(true);
    try {
      const urlSuffix = month ? `?month=${month}` : '';
      const res = await apiClient.get(`/transactions${urlSuffix}`);
      setTransactions(res.data.transactions || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    let isActive = true;

    const loadTransactions = async () => {
      setLoading(true);
      try {
        const urlSuffix = month ? `?month=${month}` : '';
        const res = await apiClient.get(`/transactions${urlSuffix}`);
        if (!isActive) return;
        setTransactions(res.data.transactions || []);
        setCurrentPage(1);
      } catch (err) {
        console.error(err);
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    };

    void loadTransactions();

    return () => {
      isActive = false;
    };
  }, [month]);

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this transaction?")) return;
    try {
      await apiClient.delete(`/transactions/${encodeURIComponent(id)}`);
      refreshTransactions();
    } catch (err) {
      alert("Delete failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    try {
      const finalAmount = editingTxn.type === 'out' ? -Math.abs(parseFloat(editingTxn.amount)) : Math.abs(parseFloat(editingTxn.amount));
      await apiClient.put(`/transactions/${encodeURIComponent(editingTxn.id)}`, {
        date: editingTxn.date,
        description: editingTxn.description,
        amount: finalAmount,
        category: editingTxn.category
      });
      setEditingTxn(null);
      refreshTransactions();
    } catch (err) {
      alert("Edit failed: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleAddSubmit = async (e) => {
    e.preventDefault();
    try {
      // If type is 'out', amount should be negative
      const finalAmount = newTxn.type === 'out' ? -Math.abs(parseFloat(newTxn.amount)) : Math.abs(parseFloat(newTxn.amount));
      await apiClient.post(`/transactions`, {
        date: newTxn.date,
        description: newTxn.description,
        amount: finalAmount,
      });
      setAddingTxn(false);
      setNewTxn({ date: new Date().toISOString().split('T')[0], description: '', amount: '', type: 'out' });
      refreshTransactions();
    } catch (err) {
      alert("Add failed: " + (err.response?.data?.detail || err.message));
    }
  };

  // Sorting logic
  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const sortedTransactions = [...transactions].sort((a, b) => {
    if (a[sortConfig.key] < b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? -1 : 1;
    }
    if (a[sortConfig.key] > b[sortConfig.key]) {
      return sortConfig.direction === 'asc' ? 1 : -1;
    }
    return 0;
  });

  // Pagination logic
  const totalPages = Math.ceil(sortedTransactions.length / itemsPerPage);
  const currentTransactions = sortedTransactions.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div>
      {/* ADD MODAL */}
      {addingTxn && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, animation: 'fadeIn 0.2s ease' }}>
          <div className="card" style={{ width: '400px', background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ marginTop: 0 }}><i className="fa-solid fa-plus" style={{color:'var(--primary)', marginRight:'8px'}}></i> Add Transaction</h3>
            <form onSubmit={handleAddSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="radio" name="type" checked={newTxn.type === 'out'} onChange={() => setNewTxn({...newTxn, type: 'out'})} /> 
                  <span style={{ color: 'var(--error)', fontWeight: 600 }}>Expense (Out)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="radio" name="type" checked={newTxn.type === 'in'} onChange={() => setNewTxn({...newTxn, type: 'in'})} /> 
                  <span style={{ color: 'var(--success)', fontWeight: 600 }}>Income (In)</span>
                </label>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Date</label>
                <input type="date" style={{ width: '100%' }} value={newTxn.date} onChange={e => setNewTxn({...newTxn, date: e.target.value})} required />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Description</label>
                <input type="text" style={{ width: '100%' }} value={newTxn.description} onChange={e => setNewTxn({...newTxn, description: e.target.value})} required />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Amount (Absolute value)</label>
                <input type="number" step="0.01" min="0" style={{ width: '100%' }} value={newTxn.amount} onChange={e => setNewTxn({...newTxn, amount: e.target.value})} required />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button type="submit" className="btn-primary" style={{ flex: 1, marginTop: '0' }}>Add</button>
                <button type="button" className="btn-outline" style={{ flex: 1 }} onClick={() => setAddingTxn(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT MODAL */}
      {editingTxn && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, animation: 'fadeIn 0.2s ease' }}>
          <div className="card" style={{ width: '400px', background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', boxShadow: '0 20px 40px rgba(0,0,0,0.2)' }}>
            <h3 style={{ marginTop: 0 }}><i className="fa-solid fa-pen-to-square" style={{color:'var(--primary)', marginRight:'8px'}}></i> Edit Transaction</h3>
            <form onSubmit={handleEditSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="radio" name="edit-type" checked={editingTxn.type === 'out'} onChange={() => setEditingTxn({...editingTxn, type: 'out'})} /> 
                  <span style={{ color: 'var(--error)', fontWeight: 600 }}>Expense (Out)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="radio" name="edit-type" checked={editingTxn.type === 'in'} onChange={() => setEditingTxn({...editingTxn, type: 'in'})} /> 
                  <span style={{ color: 'var(--success)', fontWeight: 600 }}>Income (In)</span>
                </label>
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Date</label>
                <input type="date" style={{ width: '100%' }} value={editingTxn.date} onChange={e => setEditingTxn({...editingTxn, date: e.target.value})} required />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Description</label>
                <input type="text" style={{ width: '100%' }} value={editingTxn.description} onChange={e => setEditingTxn({...editingTxn, description: e.target.value})} required />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Category</label>
                <input type="text" style={{ width: '100%' }} value={editingTxn.category} onChange={e => setEditingTxn({...editingTxn, category: e.target.value})} required />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>Amount (Absolute value)</label>
                <input type="number" step="0.01" min="0" style={{ width: '100%' }} value={editingTxn.amount} onChange={e => setEditingTxn({...editingTxn, amount: e.target.value})} required />
              </div>
              <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                <button type="submit" className="btn-primary" style={{ flex: 1, marginTop:'0' }}>Save Changes</button>
                <button type="button" className="btn-outline" style={{ flex: 1 }} onClick={() => setEditingTxn(null)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: '1.5rem'}}>
          <h3 style={{marginTop:0}}><i className="fa-solid fa-list-check" style={{color:'var(--primary)'}}></i> All Transactions</h3>
          <div style={{display:'flex', gap:'1rem', alignItems: 'center'}}>
            <button className="btn-outline" onClick={() => setAddingTxn(true)}><i className="fa-solid fa-plus"></i> Add Transaction</button>
            <div style={{display:'flex', gap:'0.5rem', alignItems: 'center'}}>
              <input type="month" value={month} onChange={e => setMonth(e.target.value)} />
              <button className="btn-primary" onClick={refreshTransactions}>Filter</button>
            </div>
          </div>
        </div>
        
        {loading ? (
           <div style={{textAlign:'center', padding:'2rem'}}><span className="spinner"></span></div>
        ) : transactions.length === 0 ? (
          <p style={{color:'var(--text-muted)'}}>No transactions found for this period.</p>
        ) : (
          <table className="txn-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('date')} style={{cursor: 'pointer'}}>Date {sortConfig.key === 'date' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th onClick={() => handleSort('description')} style={{cursor: 'pointer'}}>Description {sortConfig.key === 'description' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th onClick={() => handleSort('category')} style={{cursor: 'pointer'}}>Category {sortConfig.key === 'category' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th onClick={() => handleSort('amount')} style={{cursor: 'pointer'}}>Amount {sortConfig.key === 'amount' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {currentTransactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description}</td>
                  <td>
                    <span style={{background: 'var(--primary-light)', color: 'var(--primary-dark)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 600}}>
                      {t.category}
                    </span>
                  </td>
                  <td style={{color: t.amount >= 0 ? 'var(--success)' : 'var(--error)', fontWeight: 600}}>
                    {t.amount >= 0 ? '+' : '-'}{formatCurrency(Math.abs(t.amount))}
                  </td>
                  <td>
                    <button className="btn-outline" style={{padding:'0.3rem 0.6rem', fontSize:'0.8rem', marginRight:'0.5rem'}} onClick={() => setEditingTxn({...t, type: t.amount >= 0 ? 'in' : 'out', amount: Math.abs(t.amount)})}>Edit</button>
                    <button onClick={() => handleDelete(t.id)} style={{background:'transparent', border:'none', color:'var(--error)', cursor:'pointer'}}><i className="fa-solid fa-trash"></i></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* PAGINATION */}
        {transactions.length > itemsPerPage && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid rgba(0,0,0,0.05)' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, transactions.length)} of {transactions.length} entries</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className="btn-outline" 
                disabled={currentPage === 1} 
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                style={{ padding: '0.3rem 0.8rem', opacity: currentPage === 1 ? 0.5 : 1, cursor: currentPage === 1 ? 'not-allowed' : 'pointer' }}
              >
                Previous
              </button>
              <button 
                className="btn-outline" 
                disabled={currentPage === totalPages} 
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                style={{ padding: '0.3rem 0.8rem', opacity: currentPage === totalPages ? 0.5 : 1, cursor: currentPage === totalPages ? 'not-allowed' : 'pointer' }}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Transactions;
