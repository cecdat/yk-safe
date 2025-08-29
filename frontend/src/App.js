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
import NetworkTools from './pages/NetworkTools';
import Settings from './pages/Settings';
import AppLayout from './components/Layout/AppLayout';
import './App.css';

// 专业深色主题配置
const theme = {
  token: {
    // 主色调 - 深蓝色
    colorPrimary: '#1890ff',
    colorPrimaryHover: '#40a9ff',
    colorPrimaryActive: '#096dd9',
    
    // 辅助色
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    
    // 背景色
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f0f2f5',
    colorBgElevated: '#ffffff',
    
    // 文字颜色
    colorText: '#262626',
    colorTextSecondary: '#595959',
    colorTextTertiary: '#8c8c8c',
    
    // 边框颜色
    colorBorder: '#d9d9d9',
    colorBorderSecondary: '#f0f0f0',
    
    // 圆角
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,
    
    // 阴影
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
    boxShadowSecondary: '0 4px 16px rgba(0, 0, 0, 0.15)',
    
    // 字体
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 12,
    
    // 间距
    padding: 16,
    paddingLG: 24,
    paddingSM: 8,
    margin: 16,
    marginLG: 24,
    marginSM: 8,
  },
  components: {
    // 按钮样式
    Button: {
      borderRadius: 8,
      controlHeight: 36,
      fontWeight: 500,
    },
    // 卡片样式
    Card: {
      borderRadius: 12,
      boxShadow: '0 2px 8px rgba(127, 176, 105, 0.1)',
      headerBg: '#F5F9F2',
    },
    // 表格样式
    Table: {
      borderRadius: 12,
      headerBg: '#F5F9F2',
      headerColor: '#4A5D4A',
    },
    // 输入框样式
    Input: {
      borderRadius: 8,
      controlHeight: 36,
    },
    // 选择器样式
    Select: {
      borderRadius: 8,
      controlHeight: 36,
    },
    // 标签页样式
    Tabs: {
      borderRadius: 8,
    },
    // 菜单样式
    Menu: {
      borderRadius: 8,
      itemBorderRadius: 8,
    },
    // 模态框样式
    Modal: {
      borderRadius: 12,
    },
    // 标签样式
    Tag: {
      borderRadius: 6,
    },
    // 进度条样式
    Progress: {
      borderRadius: 4,
    },
  },
};

function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
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
            <Route path="/network-tools" element={
              <AppLayout>
                <NetworkTools />
              </AppLayout>
            } />
            <Route path="/settings" element={
              <AppLayout>
                <Settings />
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
