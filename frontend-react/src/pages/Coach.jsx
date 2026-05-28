import React, { useState } from 'react';
import apiClient from '../api/client';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { formatCurrency } from '../utils/format';

function Coach() {
  const [insights, setInsights] = useState(null);
  const [suggestedCaps, setSuggestedCaps] = useState([]);
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [handlingCap, setHandlingCap] = useState(null);

  const generateInsights = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await apiClient.get('/coach');
      if (res.data.insights) {
        setInsights(res.data.insights);
        setSuggestedCaps(res.data.suggested_caps || []);
        setChartData(res.data.chartData);
      } else {
        setError('No insights returned.');
      }
    } catch (err) {
      setError('Failed to load insights. ' + (err.message));
    }
    setLoading(false);
  };

  const acceptCap = async (cap) => {
    setHandlingCap(cap.category);
    try {
      await apiClient.post('/caps', { category: cap.category, amount: cap.suggested_cap });
      setSuggestedCaps(suggestedCaps.filter(c => c.category !== cap.category));
    } catch (err) {
      alert("Failed to set cap: " + err.message);
    }
    setHandlingCap(null);
  };

  const ignoreCap = (category) => {
    setSuggestedCaps(suggestedCaps.filter(c => c.category !== category));
  };

  const getIcon = (type) => {
    if (type === 'positive') return <i className="fa-solid fa-piggy-bank"></i>;
    if (type === 'warning') return <i className="fa-solid fa-triangle-exclamation"></i>;
    return <i className="fa-solid fa-lightbulb"></i>;
  };

  const getStyle = (type) => {
    if (type === 'positive') return { bg: 'rgba(34, 197, 94, 0.05)', border: '#22c55e', text: '#14532d', desc: '#166534' };
    if (type === 'warning') return { bg: 'rgba(239, 68, 68, 0.05)', border: '#ef4444', text: '#7f1d1d', desc: '#991b1b' }; 
    return { bg: 'rgba(59, 130, 246, 0.05)', border: '#3b82f6', text: '#1e3a8a', desc: '#1e40af' }; 
  };

  const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#06b6d4', '#f43f5e'];

  return (
    <div className="card" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h2 style={{ marginTop: 0, marginBottom: '0.5rem' }}>
          <i className="fa-solid fa-wand-magic-sparkles" style={{ color: 'var(--primary)', marginRight: '10px' }}></i> 
          AI Budget Recommendations
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', maxWidth: '600px', margin: '0 auto' }}>
          Get personalized, actionable financial advice based on a deep AI analysis of your actual spending patterns.
        </p>
      </div>
      
      <div style={{ textAlign: 'center' }}>
        <button className="btn-primary" onClick={generateInsights} disabled={loading} style={{ padding: '0.8rem 2rem', fontSize: '1.1rem', borderRadius: '30px' }}>
          {loading ? <><span className="spinner" style={{ borderColor: 'white', borderTopColor: 'transparent' }}></span> Analyzing Data...</> : <><i className="fa-solid fa-bolt"></i> Generate Smart Insights</>}
        </button>
      </div>

      {error && <div style={{ color: 'var(--error)', marginTop: '1.5rem', textAlign: 'center' }}>{error}</div>}

      <div id="coach-insights" style={{ marginTop: '2.5rem' }}>
        {!insights && !loading && (
          <div style={{ textAlign: 'center', padding: '3rem 2rem', background: 'rgba(0,0,0,0.02)', borderRadius: '16px', color: 'var(--text-muted)' }}>
            <i className="fa-solid fa-robot" style={{ fontSize: '3rem', color: '#cbd5e1', marginBottom: '1rem' }}></i>
            <p>Your AI Coach is ready to review your finances.</p>
          </div>
        )}

        {insights && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '2rem' }}>
            
            {/* Chart Section */}
            {chartData && chartData.length > 0 && (
              <div style={{ padding: '1.5rem', background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.8)', boxShadow: '0 8px 32px rgba(0,0,0,0.05)' }}>
                <h4 style={{ marginTop: 0, textAlign: 'center', color: 'var(--text-color)' }}>Spending Distribution</h4>
                <div style={{ height: '300px', width: '100%' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                        cornerRadius={4}
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        formatter={(value) => formatCurrency(value)}
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)' }}
                      />
                      <Legend verticalAlign="bottom" height={36}/>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Insights Section */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <h4 style={{ margin: 0, color: 'var(--text-color)' }}>Personalized Action Plan</h4>
              {insights.map((insight, idx) => {
                const style = getStyle(insight.type);
                return (
                  <div key={idx} style={{ padding: '1.5rem', background: style.bg, borderLeft: `5px solid ${style.border}`, borderRadius: '12px', boxShadow: '0 4px 15px rgba(0,0,0,0.03)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '0.8rem' }}>
                      <div style={{ background: style.border, color: 'white', width: '36px', height: '36px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.1rem' }}>
                        {getIcon(insight.type)}
                      </div>
                      <h4 style={{ margin: 0, color: style.text, fontSize: '1.1rem' }}>{insight.title}</h4>
                    </div>
                    <p style={{ margin: '0 0 1rem 0', fontSize: '0.95rem', color: style.desc, lineHeight: 1.5 }}>
                      {insight.description}
                    </p>
                    
                    {insight.actionable_steps && insight.actionable_steps.length > 0 && (
                      <div style={{ background: 'rgba(255,255,255,0.6)', padding: '1rem', borderRadius: '8px' }}>
                        <h5 style={{ margin: '0 0 0.8rem 0', color: style.text, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Action Items</h5>
                        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          {insight.actionable_steps.map((step, sIdx) => (
                            <li key={sIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '0.9rem', color: 'var(--text-color)' }}>
                              <i className="fa-regular fa-square-check" style={{ color: style.border, marginTop: '3px' }}></i>
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Suggested Caps Section */}
            {suggestedCaps && suggestedCaps.length > 0 && (
              <div style={{ padding: '1.5rem', background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.8)', boxShadow: '0 8px 32px rgba(0,0,0,0.05)' }}>
                <h4 style={{ marginTop: 0, color: 'var(--text-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <i className="fa-solid fa-bullseye" style={{ color: 'var(--primary)' }}></i> Suggested Budget Caps
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {suggestedCaps.map((cap, idx) => (
                    <div key={idx} style={{ padding: '1rem', background: 'rgba(255,255,255,0.6)', borderRadius: '8px', border: '1px solid rgba(0,0,0,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                      <div style={{ flex: '1 1 300px' }}>
                        <h5 style={{ margin: '0 0 0.5rem 0', color: 'var(--text-color)', fontSize: '1.1rem' }}>{cap.category}</h5>
                        <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--text-muted)' }}>{cap.reason}</p>
                        <div style={{ fontWeight: 'bold', color: 'var(--primary)', fontSize: '1.2rem' }}>{formatCurrency(cap.suggested_cap)}</div>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <button className="btn-outline" onClick={() => ignoreCap(cap.category)} disabled={handlingCap === cap.category}>Ignore</button>
                        <button className="btn-primary" style={{ marginTop: 0 }} onClick={() => acceptCap(cap)} disabled={handlingCap === cap.category}>
                          {handlingCap === cap.category ? 'Saving...' : 'Accept'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Coach;
