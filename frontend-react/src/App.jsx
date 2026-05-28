import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { UploadProvider } from './context/UploadContext';
import ProtectedRoute from './components/ProtectedRoute';
import UploadToast from './components/UploadToast';
import ReviewModal from './components/ReviewModal';

import Login from './pages/Login';
import Register from './pages/Register';

// Protected pages
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Overview from './pages/Overview';
import Transactions from './pages/Transactions';
import Chat from './pages/Chat';
import Coach from './pages/Coach';
import Limits from './pages/Limits';

function AppLayout() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'transparent' }}>
      <Sidebar />
      <main className="main-content" style={{ flex: 1, overflowY: 'auto', position: 'relative', background: 'transparent' }}>
        <Topbar />
        <div style={{ padding: '0 1rem 2rem 1rem', maxWidth: '1000px', margin: '0 auto', animation: 'fadeIn 0.4s ease' }}>
          <Outlet />
        </div>
      </main>
      <UploadToast />
      <ReviewModal />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <UploadProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route path="/overview" element={<Overview />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/coach" element={<Coach />} />
              <Route path="/limits" element={<Limits />} />
              <Route path="/" element={<Navigate to="/overview" replace />} />
            </Route>
          </Routes>
        </UploadProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
