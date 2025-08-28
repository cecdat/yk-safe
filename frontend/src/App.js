import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import FirewallRules from './pages/FirewallRules';
import Monitor from './pages/Monitor';
import Logs from './pages/Logs';
import TokenManagement from './pages/TokenManagement';
import AppLayout from './components/Layout/AppLayout';
import './App.css';

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={
              <AppLayout>
                <Dashboard />
              </AppLayout>
            } />
            <Route path="/firewall" element={
              <AppLayout>
                <FirewallRules />
              </AppLayout>
            } />
            <Route path="/token-management" element={
              <AppLayout>
                <TokenManagement />
              </AppLayout>
            } />
            <Route path="/monitor" element={
              <AppLayout>
                <Monitor />
              </AppLayout>
            } />
            <Route path="/logs" element={
              <AppLayout>
                <Logs />
              </AppLayout>
            } />
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </Router>
    </ConfigProvider>
  );
}

export default App;
