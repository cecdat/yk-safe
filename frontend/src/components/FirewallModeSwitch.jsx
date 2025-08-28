import React, { useState, useEffect } from 'react';
import { Card, Switch, Alert, Modal, Typography, Space, Button, message } from 'antd';
import { 
  SafetyOutlined, 
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  StopOutlined
} from '@ant-design/icons';
import { getFirewallConfig, updateFirewallMode } from '../api/firewall';

const { Title, Paragraph, Text } = Typography;

const FirewallModeSwitch = ({ onModeChange }) => {
  const [currentMode, setCurrentMode] = useState('blacklist');
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [pendingMode, setPendingMode] = useState(null);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await getFirewallConfig();
      setCurrentMode(response.data.mode);
    } catch (error) {
      console.error('获取防火墙配置失败:', error);
    }
  };

  const handleModeChange = (checked) => {
    const newMode = checked ? 'whitelist' : 'blacklist';
    setPendingMode(newMode);
    setModalVisible(true);
  };

  const handleConfirmModeChange = async () => {
    if (!pendingMode) return;

    setLoading(true);
    try {
      const description = pendingMode === 'whitelist' 
        ? '切换到白名单模式 - 只允许明确允许的连接'
        : '切换到黑名单模式 - 默认允许，只拒绝明确拒绝的连接';
      
      await updateFirewallMode(pendingMode, description);
      setCurrentMode(pendingMode);
      setModalVisible(false);
      setPendingMode(null);
      message.success(`防火墙模式已切换到${pendingMode === 'whitelist' ? '白名单' : '黑名单'}模式`);
      
      // 通知父组件模式已更改
      if (onModeChange) {
        onModeChange(pendingMode);
      }
    } catch (error) {
      message.error('模式切换失败');
      console.error('模式切换失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const getModeInfo = (mode) => {
    if (mode === 'whitelist') {
      return {
        title: '白名单模式',
        description: '只允许明确允许的连接，其他所有连接都会被拒绝',
        icon: <StopOutlined style={{ color: '#ff4d4f' }} />,
        color: '#ff4d4f',
        details: [
          '默认拒绝所有连接',
          '只允许明确配置的规则',
          '安全性更高，但可能影响正常服务',
          '适合高安全要求的环境'
        ]
      };
    } else {
      return {
        title: '黑名单模式',
        description: '默认允许所有连接，只拒绝明确拒绝的连接',
        icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
        color: '#52c41a',
        details: [
          '默认允许所有连接',
          '只拒绝明确配置的规则',
          '兼容性更好，但安全性相对较低',
          '适合一般使用环境'
        ]
      };
    }
  };

  const currentModeInfo = getModeInfo(currentMode);
  const pendingModeInfo = pendingMode ? getModeInfo(pendingMode) : null;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ fontSize: '14px', color: '#666' }}>模式切换:</span>
      <Switch
        checked={currentMode === 'whitelist'}
        onChange={handleModeChange}
        loading={loading}
        checkedChildren="白名单"
        unCheckedChildren="黑名单"
        size="default"
      />

      {/* 确认对话框 */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
            确认切换防火墙模式
          </Space>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setPendingMode(null);
        }}
        footer={[
          <Button 
            key="cancel" 
            onClick={() => {
              setModalVisible(false);
              setPendingMode(null);
            }}
          >
            取消
          </Button>,
          <Button 
            key="confirm" 
            type="primary" 
            danger={pendingMode === 'whitelist'}
            loading={loading}
            onClick={handleConfirmModeChange}
          >
            确认切换
          </Button>
        ]}
        width={600}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* 当前模式 */}
          <Alert
            message="当前模式"
            description={
              <div>
                <Space>
                  {currentModeInfo.icon}
                  <div>
                    <Text strong>{currentModeInfo.title}</Text>
                    <br />
                    <Text type="secondary">{currentModeInfo.description}</Text>
                  </div>
                </Space>
              </div>
            }
            type="info"
            showIcon={false}
          />

          {/* 目标模式 */}
          {pendingModeInfo && (
            <Alert
              message="目标模式"
              description={
                <div>
                  <Space>
                    {pendingModeInfo.icon}
                    <div>
                      <Text strong>{pendingModeInfo.title}</Text>
                      <br />
                      <Text type="secondary">{pendingModeInfo.description}</Text>
                    </div>
                  </Space>
                </div>
              }
              type={pendingMode === 'whitelist' ? 'warning' : 'info'}
              showIcon={false}
            />
          )}

          {/* 切换后果警告 */}
          <Alert
            message="切换后果"
            description={
              <div>
                <Paragraph style={{ marginBottom: 8 }}>
                  <Text strong>⚠️ 重要提醒：</Text>
                </Paragraph>
                <ul style={{ margin: 0, paddingLeft: 16 }}>
                  {pendingMode === 'whitelist' ? (
                    <>
                      <li>切换到白名单模式后，所有未明确允许的连接都会被拒绝</li>
                      <li>可能导致现有服务无法访问</li>
                      <li>需要重新配置防火墙规则</li>
                      <li>建议在维护窗口期间进行切换</li>
                    </>
                  ) : (
                    <>
                      <li>切换到黑名单模式后，所有连接默认允许</li>
                      <li>安全性相对降低</li>
                      <li>需要重新配置防火墙规则</li>
                    </>
                  )}
                </ul>
              </div>
            }
            type="warning"
            showIcon
            icon={<ExclamationCircleOutlined />}
          />

          {/* 操作确认 */}
          <Alert
            message="操作确认"
            description="请确认您了解切换模式的后果，并确保有相应的应急方案。"
            type="info"
            showIcon
          />
        </Space>
      </Modal>
    </div>
  );
};

export default FirewallModeSwitch;
