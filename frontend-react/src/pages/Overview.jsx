import React, { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { formatCurrency } from '../utils/format';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

function Overview() {
  const [file, setFile] = useState(null);
  const [uploadMsg, setUploadMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [summaryData, setSummaryData] = useState(null);
  const [month, setMonth] = useState('');
  const [transactions, setTransactions] = useState([]);
  const [reviewTransactions, setReviewTransactions] = useState([]);

  // Fetch summary and transactions
  const fetchData = async () => {
    setLoading(true);
    try {
      const urlSuffix = month ? `?month=${month}` : '';
      const [sumRes, txnRes] = await Promise.all([
        apiClient.get(`/summary${urlSuffix}`),
        apiClient.get(`/transactions${urlSuffix}`)
      ]);
      setSummaryData(sumRes.data);
      setTransactions(txnRes.data.transactions || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [month]);

  const handleUpload = async (f) => {
    if (!f) return;
    setUploadMsg('Uploading & Categorizing...');
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await apiClient.post('/upload', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const needsReview = res.data.needs_review || [];
      if (needsReview.length > 0) {
        setUploadMsg(`Success! ${res.data.rows_inserted} transactions stored. ${needsReview.length} need manual review.`);
        setReviewTransactions(needsReview);
      } else {
        setUploadMsg(`Success! ${res.data.rows_inserted} transactions categorized and stored.`);
      }
      fetchData();
    } catch (err) {
      setUploadMsg('Upload failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDragOver = (e) => { e.preventDefault(); e.currentTarget.classList.add('dragover'); };
  const handleDragLeave = (e) => { e.preventDefault(); e.currentTarget.classList.remove('dragover'); };
  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this transaction?")) return;
    try {
      await apiClient.delete(`/transactions/${id}`);
      fetchData();
    } catch (err) {
      alert("Delete failed");
    }
  };

  const handleReviewSave = async () => {
    try {
      setUploadMsg('Saving reviewed transactions...');
      await apiClient.post('/transactions/batch', { transactions: reviewTransactions });
      setUploadMsg(`Saved ${reviewTransactions.length} reviewed transactions successfully.`);
      setReviewTransactions([]);
      fetchData();
    } catch (err) {
      setUploadMsg('Batch save failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReviewCategoryChange = (index, newCat) => {
    const updated = [...reviewTransactions];
    updated[index].category = newCat;
    setReviewTransactions(updated);
  };

  return (
    <div>
      {/* REVIEW MODAL */}
      {reviewTransactions.length > 0 && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, 
          backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div className="card" style={{ width: '90%', maxWidth: '700px', maxHeight: '80vh', overflowY: 'auto' }}>
            <h3 style={{marginTop: 0, color: 'var(--error)'}}>
              <i className="fa-solid fa-triangle-exclamation"></i> Manual Review Required
            </h3>
            <p style={{color: 'var(--text-muted)'}}>
              The AI was not confident about the following {reviewTransactions.length} transaction(s). 
              Please confirm or update their categories before saving.
            </p>
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
              <button className="btn" onClick={() => setReviewTransactions([])} style={{ background: '#e5e7eb', color: '#374151' }}>Cancel All</button>
              <button className="btn-primary" onClick={handleReviewSave}>Confirm & Save All</button>
            </div>
          </div>
        </div>
      )}

      {/* UPLOAD SECTION */}
      <div className="card">
        <h3 style={{marginTop:0}}><i className="fa-solid fa-file-csv" style={{color:'var(--primary)'}}></i> Upload Bank Statement</h3>
        <label 
          className="drop" 
          onDragOver={handleDragOver} 
          onDragLeave={handleDragLeave} 
          onDrop={handleDrop}
          style={{ display: 'block' }}
        >
          <i className="fa-solid fa-cloud-arrow-up" style={{fontSize: '2.5rem', color: 'var(--primary)', marginBottom: '1rem'}}></i>
          <p><strong>Drag a CSV here</strong> or click to browse</p>
          <p style={{fontSize:'0.8rem', color:'var(--text-muted)'}}>Supported: .csv, .pdf, .png, .jpg</p>
          <input type="file" accept=".csv,.txt,.pdf,.png,.jpg,.jpeg" style={{display:'none'}} onChange={(e) => handleUpload(e.target.files[0])} />
        </label>
        {uploadMsg && (
          <div style={{marginTop:'1rem', padding:'1rem', background:'#f0fdf4', border:'1px solid #bbf7d0', borderRadius:'8px', color:'#166534'}}>
            {uploadMsg}
          </div>
        )}
      </div>

      {/* SUMMARY SECTION */}
      <div className="card">
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom: '1.5rem'}}>
          <h3 style={{margin:0}}><i className="fa-solid fa-chart-column" style={{color:'var(--primary)'}}></i> Spending Summary</h3>
          <div>
            <input type="month" value={month} onChange={e => setMonth(e.target.value)} />
            <button className="btn-primary" style={{marginLeft: '0.5rem'}} onClick={fetchData}>Filter</button>
          </div>
        </div>

        {loading ? (
          <div style={{textAlign:'center', padding:'2rem'}}><span className="spinner"></span></div>
        ) : (!summaryData || !summaryData.by_category || Object.keys(summaryData.by_category).length === 0) ? (
          <div style={{textAlign:'center', padding:'2rem', color:'var(--text-muted)'}}>No data available. Please upload a statement.</div>
        ) : (
          <>
            <div className="summary-totals" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
              {(() => {
                const byCat = summaryData.by_category;
                const incomes = Object.values(byCat).filter(v => v.total > 0).reduce((s, v) => s + v.total, 0);
                const expenses = Object.values(byCat).filter(v => v.total < 0).reduce((s, v) => s + Math.abs(v.total), 0);
                const net = incomes - expenses;
                const maxBar = Math.max(...Object.values(byCat).map(v => Math.abs(v.total)), 1);
                
                return (
                  <>
                    <div className="total-tile" style={{padding:'1.5rem', background:'rgba(255,255,255,0.4)', borderRadius:'20px', border:'1px solid rgba(255,255,255,0.8)', boxShadow: '0 8px 32px rgba(0,0,0,0.05)', position:'relative', overflow:'hidden'}}>
                      <div style={{position:'absolute', top:'-20px', right:'-20px', width:'80px', height:'80px', background:'var(--success)', opacity:0.1, borderRadius:'50%', filter:'blur(20px)'}}></div>
                      <div className="label" style={{color:'var(--text-muted)', fontSize:'0.85rem', textTransform:'uppercase', fontWeight:700, letterSpacing:'0.5px'}}>Total Income</div>
                      <div className="value" style={{fontSize:'2rem', fontWeight:800, marginTop:'0.5rem', color:'var(--success)'}}>{formatCurrency(incomes)}</div>
                    </div>
                    <div className="total-tile" style={{padding:'1.5rem', background:'rgba(255,255,255,0.4)', borderRadius:'20px', border:'1px solid rgba(255,255,255,0.8)', boxShadow: '0 8px 32px rgba(0,0,0,0.05)', position:'relative', overflow:'hidden'}}>
                      <div style={{position:'absolute', top:'-20px', right:'-20px', width:'80px', height:'80px', background:'var(--error)', opacity:0.1, borderRadius:'50%', filter:'blur(20px)'}}></div>
                      <div className="label" style={{color:'var(--text-muted)', fontSize:'0.85rem', textTransform:'uppercase', fontWeight:700, letterSpacing:'0.5px'}}>Total Expenses</div>
                      <div className="value" style={{fontSize:'2rem', fontWeight:800, marginTop:'0.5rem', color:'var(--error)'}}>{formatCurrency(expenses)}</div>
                    </div>
                    <div className="total-tile" style={{padding:'1.5rem', background:'rgba(255,255,255,0.4)', borderRadius:'20px', border:'1px solid rgba(255,255,255,0.8)', boxShadow: '0 8px 32px rgba(0,0,0,0.05)', position:'relative', overflow:'hidden'}}>
                      <div style={{position:'absolute', top:'-20px', right:'-20px', width:'80px', height:'80px', background: net >= 0 ? 'var(--success)' : 'var(--error)', opacity:0.1, borderRadius:'50%', filter:'blur(20px)'}}></div>
                      <div className="label" style={{color:'var(--text-muted)', fontSize:'0.85rem', textTransform:'uppercase', fontWeight:700, letterSpacing:'0.5px'}}>Net Savings</div>
                      <div className="value" style={{fontSize:'2rem', fontWeight:800, marginTop:'0.5rem', color: net >= 0 ? 'var(--success)' : 'var(--error)'}}>{net >= 0 ? '' : '-'}{formatCurrency(Math.abs(net))}</div>
                    </div>
                  </>
                )
              })()}
            </div>
            <div>
              <h4 style={{marginTop:0, marginBottom:'1.5rem', borderBottom:'1px solid rgba(0,0,0,0.05)', paddingBottom:'0.5rem'}}>Spending Breakdown</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', alignItems: 'center' }}>
                <div style={{ flex: '1 1 300px', height: '300px' }}>
                  {(() => {
                    const data = Object.entries(summaryData.by_category)
                      .filter(([_, v]) => v.total < 0)
                      .map(([name, v]) => ({ name, value: Math.abs(v.total) }))
                      .sort((a, b) => b.value - a.value);
                      
                    const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#f43f5e'];

                    if (data.length === 0) return <div style={{textAlign:'center', color:'var(--text-muted)', marginTop:'50px'}}>No expenses to chart.</div>;

                    return (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={data}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={100}
                            paddingAngle={5}
                            dataKey="value"
                            stroke="none"
                            cornerRadius={4}
                          >
                            {data.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip 
                            formatter={(value) => formatCurrency(value)}
                            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    );
                  })()}
                </div>
                
                <div style={{ flex: '1 1 300px' }}>
                  {Object.entries(summaryData.by_category).filter(([_, v]) => v.total < 0).sort((a,b) => Math.abs(b[1].total) - Math.abs(a[1].total)).map(([cat, v], idx) => {
                    const isIncome = v.total >= 0;
                    const maxBar = Math.max(...Object.values(summaryData.by_category).filter(val => val.total < 0).map(val => Math.abs(val.total)), 1);
                    const pct = Math.round((Math.abs(v.total) / maxBar) * 100);
                    const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#f43f5e'];
                    const color = isIncome ? 'var(--success)' : COLORS[idx % COLORS.length];
                    
                    return (
                      <div key={cat} style={{ display: 'grid', gridTemplateColumns: '140px 1fr 100px', alignItems: 'center', gap: '1.5rem', marginBottom: '1rem' }}>
                        <div style={{fontWeight: 600, fontSize:'0.95rem'}}>{cat}</div>
                        <div style={{ height: '12px', background: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.8)', borderRadius: '6px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', borderRadius: '6px', transition: 'width 1s cubic-bezier(0.4, 0, 0.2, 1)', width: `${pct}%`, background: color, boxShadow: `0 0 10px ${color}80` }}></div>
                        </div>
                        <div style={{ textAlign: 'right', fontWeight: 700, color: 'var(--text-muted)' }}>
                          {isIncome ? '+' : ''}{formatCurrency(Math.abs(v.total))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default Overview;
