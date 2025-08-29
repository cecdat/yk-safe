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

// 现代化科技感主题配置
const theme = {
  token: {
    // 核心色彩体系
    colorPrimary: '#3B82F6',           // 科技蓝 - 主色调
    colorPrimaryHover: '#2563EB',      // 主色调悬停状态
    colorPrimaryActive: '#1D4ED8',     // 主色调激活状态
    
    // 状态色彩
    colorSuccess: '#10B981',           // 活力青 - 成功色
    colorWarning: '#F59E0B',           // 警告黄 - 警告色
    colorError: '#EF4444',             // 危险红 - 错误色
    colorInfo: '#3B82F6',              // 信息色 - 与主色调一致
    
    // 背景色系
    colorBgContainer: '#FFFFFF',       // 纯白 - 容器背景
    colorBgLayout: '#F9FAFB',          // 浅灰 - 布局背景
    colorBgElevated: '#FFFFFF',        // 纯白 - 提升背景
    
    // 文字色系
    colorText: '#111827',              // 深灰 - 主文字色
    colorTextSecondary: '#6B7281',     // 中灰 - 次要文字色
    colorTextTertiary: '#9CA3AF',      // 浅灰 - 辅助文字色
    
    // 边框和分割线
    colorBorder: '#E5E7EB',            // 弱灰 - 边框色
    colorBorderSecondary: '#F3F4F6',   // 更浅的边框色
    
    // 设计系统
    borderRadius: 8,                   // 统一圆角
    borderRadiusLG: 12,                // 大圆角
    borderRadiusSM: 6,                 // 小圆角
    
    // 阴影系统
    boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    boxShadowSecondary: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    
    // 字体系统
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 12,
    fontWeight: 400,
    fontWeightStrong: 600,
    
    // 间距系统
    padding: 16,
    paddingLG: 24,
    paddingSM: 8,
    margin: 16,
    marginLG: 24,
    marginSM: 8,
    
    // 动画
    motionDurationFast: '0.1s',
    motionDurationMid: '0.2s',
    motionDurationSlow: '0.3s',
  },
  components: {
    // 布局组件
    Layout: {
      siderBg: '#1F2937',           // 侧边栏背景
      headerBg: '#FFFFFF',           // 顶部栏背景
      bodyBg: '#F9FAFB',            // 主体背景
    },
    // 菜单组件
    Menu: {
      darkItemBg: '#1F2937',        // 侧边栏菜单背景
      darkSubMenuItemBg: '#111827', // 子菜单背景
      darkItemHoverBg: '#374151',   // 悬停背景
      darkItemSelectedBg: '#3B82F6', // 选中背景
      borderRadius: 6,               // 菜单项圆角
    },
    // 按钮样式
    Button: {
      borderRadius: 6,
      controlHeight: 36,
      fontWeight: 500,
      primaryShadow: '0 1px 3px 0 rgb(59 130 246 / 0.3)',
    },
    // 卡片样式
    Card: {
      borderRadius: 8,
      headerBg: '#FFFFFF',
      headerColor: '#111827',
      boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    },
    // 表格样式
    Table: {
      borderRadius: 8,
      headerBg: '#F9FAFB',
      headerColor: '#111827',
      rowHoverBg: '#F3F4F6',
    },
    // 输入框样式
    Input: {
      borderRadius: 6,
      controlHeight: 36,
      borderColor: '#E5E7EB',
      hoverBorderColor: '#3B82F6',
    },
    // 选择器样式
    Select: {
      borderRadius: 6,
      controlHeight: 36,
      borderColor: '#E5E7EB',
      hoverBorderColor: '#3B82F6',
    },
    // 标签页样式
    Tabs: {
      borderRadius: 6,
      itemSelectedColor: '#3B82F6',
      inkBarColor: '#3B82F6',
    },
    // 模态框样式
    Modal: {
      borderRadius: 12,
      headerBg: '#FFFFFF',
      contentBg: '#FFFFFF',
    },
    // 标签样式
    Tag: {
      borderRadius: 6,
      colorBgContainer: '#F3F4F6',
    },
    // 进度条样式
    Progress: {
      borderRadius: 4,
      defaultColor: '#3B82F6',
      successColor: '#10B981',
    },
    // 开关样式
    Switch: {
      borderRadius: 6,
      colorPrimary: '#3B82F6',
      colorPrimaryHover: '#2563EB',
    },
    // 分页样式
    Pagination: {
      borderRadius: 6,
      itemActiveBg: '#3B82F6',
      itemActiveBorderColor: '#3B82F6',
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
