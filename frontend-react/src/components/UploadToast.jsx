import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useUpload } from '../context/UploadContext';
import './UploadToast.css';

function UploadToast() {
  const { toasts, removeToast, activeJobCount, setReviewTransactions } = useUpload();
  const navigate = useNavigate();

  const handleToastClick = (toast) => {
    removeToast(toast.id);
    if (toast.type === 'success') {
      if (toast.needsReview && toast.needsReview.length > 0) {
        const txnsWithJobId = toast.needsReview.map(t => ({ ...t, jobId: toast.jobId }));
        setReviewTransactions(prev => {
          const filtered = prev.filter(t => t.jobId !== toast.jobId);
          return [...filtered, ...txnsWithJobId];
        });
      }
      navigate('/transactions');
    }
  };

  return (
    <>
      {/* Processing indicator - floating pill */}
      {activeJobCount > 0 && (
        <div className="upload-processing-pill">
          <span className="processing-spinner"></span>
          <span>Processing {activeJobCount} file{activeJobCount > 1 ? 's' : ''}...</span>
        </div>
      )}

      {/* Toast notifications */}
      <div className="toast-container">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast-item toast-${toast.type}`}
            onClick={() => handleToastClick(toast)}
          >
            <div className="toast-icon">
              {toast.type === 'success' ? (
                <i className="fa-solid fa-circle-check"></i>
              ) : (
                <i className="fa-solid fa-circle-xmark"></i>
              )}
            </div>
            <div className="toast-content">
              <div className="toast-title">{toast.title}</div>
              <div className="toast-message">{toast.message}</div>
              {toast.type === 'success' && (
                <div className="toast-action">Click to view transactions →</div>
              )}
            </div>
            <button
              className="toast-close"
              onClick={(e) => { e.stopPropagation(); removeToast(toast.id); }}
            >
              <i className="fa-solid fa-xmark"></i>
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

export default UploadToast;
