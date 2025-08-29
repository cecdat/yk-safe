import React, { useState, useEffect } from 'react';
import { Layout, Menu, Avatar, Space, Typography, Tag, message, Button, Dropdown } from 'antd';
import {
  SafetyOutlined,
  MonitorOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ToolOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import FirewallModeSwitch from '../FirewallModeSwitch';
import { getFirewallConfig } from '../../api/firewall';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const AppLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [firewallStatus, setFirewallStatus] = useState(null);
  const [firewallConfig, setFirewallConfig] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 检查登录状态
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    // 获取防火墙状态和配置
    fetchFirewallData();
  }, [navigate]);

  const fetchFirewallData = async () => {
    try {
      const [statusResponse, configResponse] = await Promise.all([
        fetch('/api/firewall/status', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }),
        getFirewallConfig()
      ]);
      
      // 处理状态响应
      if (statusResponse.ok) {
        const data = await statusResponse.json();
        setFirewallStatus(data.data || { is_running: false });
      }
      
      // 处理配置响应
      if (configResponse && configResponse.data) {
        setFirewallConfig(configResponse.data);
      }
    } catch (error) {
      console.error('Failed to fetch firewall status or config:', error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    message.success('已退出登录');
    navigate('/login', { replace: true });
  };

  const getFirewallStatusTag = () => {
    if (!firewallStatus) return <Tag color="default">加载中...</Tag>;
    return firewallStatus.is_running
      ? <Tag color="success">运行中</Tag>
      : <Tag color="error">已停止</Tag>;
  };

  const userMenu = (
    <Menu>
      <Menu.Item key="logout" icon={<LogoutOutlined />} onClick={handleLogout}>
        退出登录
      </Menu.Item>
    </Menu>
  );

  const menuItems = [
    {
      key: '/dashboard',
      icon: <MonitorOutlined />,
      label: '仪表盘',
    },
    {
      key: '/firewall',
      icon: <SafetyOutlined />,
      label: '规则管理',
    },
    {
      key: '/token-management',
      icon: <SafetyOutlined />,
      label: 'Token管理',
    },
    {
      key: '/monitor',
      icon: <MonitorOutlined />,
      label: '网络监控',
    },
    {
      key: '/logs',
      icon: <FileTextOutlined />,
      label: '系统日志',
    },
    {
      key: '/network-tools',
      icon: <ToolOutlined />,
      label: '网络工具',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  // 修改防火墙状态和模式显示区域
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div style={{ 
          height: 32, 
          margin: 16, 
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? '12px' : '16px',
          fontWeight: 'bold'
        }}>
          {collapsed ? 'YK' : 'YK-Safe'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
                <Header style={{
          padding: '0 24px',
          background: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--color-border)'
        }}>
          {/* Left Side: Menu Toggle */}
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />

          {/* Center: Firewall Controls */}
          <Space size="large">
            <Space>
              <Text strong>防火墙状态:</Text>
              {getFirewallStatusTag()}
            </Space>
            <FirewallModeSwitch
              status={firewallStatus}
              setStatus={setFirewallStatus}
              config={firewallConfig}
              setConfig={setFirewallConfig}
            />
          </Space>

          {/* Right Side: User Info */}
          <Space size="middle">
            <Avatar size="small" icon={<UserOutlined />} />
            <Text strong>管理员</Text>
            <Dropdown overlay={userMenu} placement="bottomRight">
              <Button type="text" icon={<LogoutOutlined />} size="small">
                退出
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ 
          margin: '16px',
          padding: '24px',
          background: '#fff',
          borderRadius: 8,
          minHeight: 280
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
