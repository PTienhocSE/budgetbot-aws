import React, { createContext, useContext, useState, useRef, useCallback } from 'react';
import apiClient from '../api/client';

const UploadContext = createContext(null);

export function useUpload() {
  return useContext(UploadContext);
}

export function UploadProvider({ children }) {
  // Active jobs: { [jobId]: { status, filename, ... } }
  const [jobs, setJobs] = useState({});
  // Toast notification queue
  const [toasts, setToasts] = useState([]);
  const [reviewTransactions, setReviewTransactions] = useState([]);
  
  // Refresh trigger to avoid window.reload()
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const triggerRefresh = useCallback(() => setRefreshTrigger(p => p + 1), []);
  
  const pollRefs = useRef({});

  const addToast = useCallback((toast) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, ...toast }]);
    // Auto-dismiss after 8 seconds if not clicked
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 8000);
    return id;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const startPolling = useCallback((jobId) => {
    if (pollRefs.current[jobId]) return; // Already polling

    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/upload/status/${encodeURIComponent(jobId)}`);
        const data = res.data;

        setJobs(prev => ({
          ...prev,
          [jobId]: data,
        }));

        if (data.status === 'COMPLETED') {
          clearInterval(pollRefs.current[jobId]);
          delete pollRefs.current[jobId];

          const reviewCount = data.needs_review ? data.needs_review.length : 0;
          let msg = `${data.filename}: ${data.rows_inserted} transactions processed.`;
          let title = 'Upload Complete!';
          
          if (reviewCount > 0) {
            msg += ` ${reviewCount} transaction(s) need manual review.`;
            title = 'Action Required';
            // Auto-trigger the review modal immediately!
            const txnsWithJobId = data.needs_review.map(t => ({ ...t, jobId }));
            setReviewTransactions(prev => {
              const filtered = prev.filter(t => t.jobId !== jobId);
              return [...filtered, ...txnsWithJobId];
            });
          }

          addToast({
            type: 'success',
            title: title,
            message: msg,
            jobId,
            needsReview: data.needs_review || [],
          });
        } else if (data.status === 'FAILED') {
          clearInterval(pollRefs.current[jobId]);
          delete pollRefs.current[jobId];

          addToast({
            type: 'error',
            title: 'Upload Failed',
            message: `${data.filename}: ${data.error_message || 'Unknown error'}`,
            jobId,
          });
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 3000); // Poll every 3 seconds

    pollRefs.current[jobId] = interval;
  }, [addToast]);

  const submitUpload = useCallback(async (file) => {
    const fd = new FormData();
    fd.append('file', file);

    const res = await apiClient.post('/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    const { job_id, filename, status } = res.data;

    // Register the job
    setJobs(prev => ({
      ...prev,
      [job_id]: { status, filename, job_id },
    }));

    // Start polling for this job
    startPolling(job_id);

    return res.data;
  }, [startPolling]);

  // Count active (processing) jobs
  const activeJobCount = Object.values(jobs).filter(
    j => j.status === 'PENDING' || j.status === 'PROCESSING'
  ).length;

  const value = {
    jobs,
    toasts,
    activeJobCount,
    reviewTransactions,
    setReviewTransactions,
    submitUpload,
    removeToast,
    refreshTrigger,
    triggerRefresh,
  };

  return (
    <UploadContext.Provider value={value}>
      {children}
    </UploadContext.Provider>
  );
}
