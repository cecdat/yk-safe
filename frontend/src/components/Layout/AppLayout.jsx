// 导入部分保持不变
import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Dropdown, Space, message, Badge, Switch, Modal } from 'antd';
import {
  SafetyOutlined,
  MonitorOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ToolOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { getFirewallConfig, startFirewall, stopFirewall, updateFirewallMode } from '../../api/firewall';

const { Header, Sider, Content } = Layout;

const AppLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [firewallStatus, setFirewallStatus] = useState({ is_running: false });
  const [firewallMode, setFirewallMode] = useState('blacklist');
  const [modeSwitchLoading, setModeSwitchLoading] = useState(false);
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

  // 模式切换处理函数
  const handleModeSwitch = async (checked) => {
    const newMode = checked ? 'whitelist' : 'blacklist';
    const oldMode = firewallMode;
    
    // 二次确认
    Modal.confirm({
      title: '确认切换防火墙模式',
      content: (
        <div>
          <p><strong>当前模式：</strong>{oldMode === 'whitelist' ? '白名单模式' : '黑名单模式'}</p>
          <p><strong>切换为：</strong>{newMode === 'whitelist' ? '白名单模式' : '黑名单模式'}</p>
          <div style={{ marginTop: 16, padding: 12, backgroundColor: '#fff7e6', border: '1px solid #ffd591', borderRadius: 6 }}>
            <p style={{ margin: 0, color: '#d46b08', fontWeight: 'bold' }}>⚠️ 重要提醒：</p>
            <ul style={{ margin: '8px 0 0 0', paddingLeft: 20, color: '#d46b08' }}>
              <li>模式切换将影响所有现有规则的生效方式</li>
              <li>白名单模式：只允许明确允许的连接</li>
              <li>黑名单模式：默认允许所有连接，只拒绝明确拒绝的连接</li>
              <li>切换后请检查现有规则是否符合新的模式要求</li>
            </ul>
          </div>
        </div>
      ),
      okText: '确认切换',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        setModeSwitchLoading(true);
        try {
          await updateFirewallMode(newMode, `从${oldMode === 'whitelist' ? '白名单' : '黑名单'}模式切换到${newMode === 'whitelist' ? '白名单' : '黑名单'}模式`);
          message.success(`防火墙模式已切换到${newMode === 'whitelist' ? '白名单' : '黑名单'}模式`);
          setFirewallMode(newMode);
        } catch (error) {
          message.error('模式切换失败');
          console.error('Mode switch error:', error);
        } finally {
          setModeSwitchLoading(false);
        }
      },
      onCancel: () => {
        // 取消时不需要做任何操作，Switch会自动回弹
      }
    });
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
                         {/* 防火墙控制区域 - 透明化设计 */}
             <div style={{
               display: 'flex',
               alignItems: 'center',
               gap: '16px',
               padding: '8px 16px',
               background: 'transparent'
             }}>
               {/* 防火墙状态 */}
               <div style={{
                 display: 'flex',
                 alignItems: 'center',
                 gap: '6px',
                 padding: '4px 8px',
                 borderRadius: '6px',
                 background: firewallStatus.is_running ? 'rgba(40, 167, 69, 0.1)' : 'rgba(220, 53, 69, 0.1)',
                 border: `1px solid ${firewallStatus.is_running ? 'rgba(40, 167, 69, 0.3)' : 'rgba(220, 53, 69, 0.3)'}`,
                 color: firewallStatus.is_running ? '#198754' : '#dc3545',
                 fontSize: '12px',
                 fontWeight: '500'
               }}>
                 {firewallStatus.is_running ? 
                   <CheckCircleOutlined style={{ fontSize: '12px' }} /> : 
                   <ExclamationCircleOutlined style={{ fontSize: '12px' }} />
                 }
                 <span>
                   {firewallStatus.is_running ? '运行中' : '已停止'}
                 </span>
               </div>
               
               {/* 防火墙模式 */}
               <div style={{
                 padding: '4px 8px',
                 borderRadius: '6px',
                 background: 'rgba(13, 110, 253, 0.1)',
                 border: '1px solid rgba(13, 110, 253, 0.3)',
                 color: '#0d6efd',
                 fontSize: '12px',
                 fontWeight: '500'
               }}>
                 {firewallMode === 'blacklist' ? '黑名单模式' : firewallMode === 'whitelist' ? '白名单模式' : '未知模式'}
               </div>
               
               {/* 防火墙启停控制 */}
               <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                 <span style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500' }}>启停</span>
                 <Switch
                   checked={firewallStatus.is_running}
                   onChange={handleFirewallToggle}
                   checkedChildren="开"
                   unCheckedChildren="关"
                   size="small"
                   style={{ 
                     minWidth: '40px',
                     height: '18px'
                   }}
                 />
               </div>
               
               {/* 模式切换控制 */}
               <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                 <span style={{ fontSize: '12px', color: '#6c757d', fontWeight: '500' }}>模式</span>
                 <Switch
                   checked={firewallMode === 'whitelist'}
                   onChange={handleModeSwitch}
                   checkedChildren="白"
                   unCheckedChildren="黑"
                   size="small"
                   loading={modeSwitchLoading}
                   style={{ 
                     minWidth: '40px',
                     height: '18px'
                   }}
                 />
               </div>
             </div>
            
            <Dropdown overlay={userMenu} placement="bottomRight">
              <Button type="text" icon={<UserOutlined />} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Badge count={0} size="default" style={{ marginRight: '8px' }}>
                  <span>管理员</span>
                </Badge>
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
