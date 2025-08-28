// 导入部分保持不变
import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Dropdown, Space, message, Badge } from 'antd';
import {
  SafetyOutlined,
  MonitorOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { getFirewallConfig, startFirewall, stopFirewall } from '../../api/firewall';

const { Header, Sider, Content } = Layout;

const AppLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [firewallStatus, setFirewallStatus] = useState({ is_running: false });
  const [firewallMode, setFirewallMode] = useState('blacklist');
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 检查登录状态
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }

    // 获取防火墙状态
    fetchFirewallStatus();
  }, [navigate]);

  // 更新fetchFirewallStatus函数，同时获取防火墙模式
  const fetchFirewallStatus = async () => {
    try {
      const [statusResponse, configResponse] = await Promise.all([
        fetch('/api/firewall/status', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }),
        getFirewallConfig()  // 同时获取防火墙配置
      ]);
      
      // 处理状态响应
      if (statusResponse.ok) {
        const data = await statusResponse.json();
        setFirewallStatus(data.data || { is_running: false });
      }
      
      // 处理配置响应
      if (configResponse && configResponse.data && configResponse.data.mode) {
        setFirewallMode(configResponse.data.mode);
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

  const handleFirewallToggle = async (checked) => {
    try {
      if (checked) {
        await startFirewall();
        message.success('防火墙启动成功');
      } else {
        await stopFirewall();
        message.success('防火墙停止成功');
      }
      fetchFirewallStatus();
    } catch (error) {
      message.error(checked ? '防火墙启动失败' : '防火墙停止失败');
      console.error('Firewall toggle error:', error);
    }
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
          padding: '0 16px', 
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
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
          <Space>
            {/* 防火墙控制区域 */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              padding: '8px 16px',
              background: 'rgba(0, 0, 0, 0.02)',
              borderRadius: '8px',
              border: '1px solid rgba(0, 0, 0, 0.06)'
            }}>
              {/* 防火墙状态 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                {firewallStatus.is_running ? 
                  <CheckCircleOutlined style={{ fontSize: '14px', color: '#52c41a' }} /> : 
                  <ExclamationCircleOutlined style={{ fontSize: '14px', color: '#ff4d4f' }} />
                }
                <span style={{
                  fontSize: '13px',
                  fontWeight: '500',
                  color: firewallStatus.is_running ? '#52c41a' : '#ff4d4f'
                }}>
                  {firewallStatus.is_running ? '运行中' : '已停止'}
                </span>
              </div>
              
              {/* 分隔线 */}
              <div style={{ width: '1px', height: '20px', background: 'rgba(0, 0, 0, 0.1)' }} />
              
              {/* 防火墙模式 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{
                  fontSize: '13px',
                  fontWeight: '500',
                  color: '#333'
                }}>
                  {firewallMode === 'blacklist' ? '黑名单模式' : firewallMode === 'whitelist' ? '白名单模式' : '未知模式'}
                </span>
              </div>
              
              {/* 分隔线 */}
              <div style={{ width: '1px', height: '20px', background: 'rgba(0, 0, 0, 0.1)' }} />
              
              {/* 防火墙启停控制 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', color: '#666' }}>启停:</span>
                <Switch
                  checked={firewallStatus.is_running}
                  onChange={handleFirewallToggle}
                  checkedChildren="运行"
                  unCheckedChildren="停止"
                  size="small"
                  style={{ minWidth: '50px' }}
                />
              </div>
            </div>
            
            <Dropdown overlay={userMenu} placement="bottomRight">
              <Button type="text" icon={<UserOutlined />}>
                管理员
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
