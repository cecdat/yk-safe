import React, { useState, useEffect } from 'react';
import {
  Card,
  Tabs,
  Form,
  Input,
  Button,
  Space,
  message,
  Upload,
  Table,
  Modal,
  Switch,
  Select,
  Row,
  Col,
  Typography,
  Divider,
  Tag,
  Alert,
  Descriptions,
  Badge
} from 'antd';
import {
  LockOutlined,
  UploadOutlined,
  DownloadOutlined,
  DeleteOutlined,
  BellOutlined,
  SaveOutlined,
  ExperimentOutlined,
  ReloadOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { Password } = Input;

const Settings = () => {
  const [passwordForm] = Form.useForm();
  const [backupForm] = Form.useForm();
  const [pushForm] = Form.useForm();
  const [backupHistory, setBackupHistory] = useState([]);
  const [pushSettings, setPushSettings] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchBackupHistory();
    fetchPushSettings();
  }, []);

  const fetchBackupHistory = async () => {
    try {
      const response = await fetch('/api/settings/backup-history', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setBackupHistory(data.data || []);
      }
    } catch (error) {
      console.error('获取备份历史失败:', error);
    }
  };

  const fetchPushSettings = async () => {
    try {
      const response = await fetch('/api/settings/push-config', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setPushSettings(data.data || {});
        pushForm.setFieldsValue(data.data || {});
      }
    } catch (error) {
      console.error('获取推送设置失败:', error);
    }
  };

  // 密码修改
  const handlePasswordChange = async (values) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/settings/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          old_password: values.old_password,
          new_password: values.new_password
        })
      });

      if (response.ok) {
        message.success('密码修改成功');
        passwordForm.resetFields();
      } else {
        const data = await response.json();
        throw new Error(data.message || '密码修改失败');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  // 数据备份
  const handleCreateBackup = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/settings/create-backup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        message.success('备份创建成功');
        fetchBackupHistory();
      } else {
        throw new Error('备份创建失败');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadBackup = async (backupId) => {
    try {
      const response = await fetch(`/api/settings/download-backup/${backupId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backup_${backupId}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        message.success('下载成功');
      }
    } catch (error) {
      message.error('下载失败');
    }
  };

  const handleDeleteBackup = async (backupId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个备份文件吗？',
      onOk: async () => {
        try {
          const response = await fetch(`/api/settings/delete-backup/${backupId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });

          if (response.ok) {
            message.success('删除成功');
            fetchBackupHistory();
          }
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const handleRestoreBackup = async (backupId) => {
    Modal.confirm({
      title: '确认恢复',
      content: '恢复备份将覆盖当前数据，确定要继续吗？',
      okType: 'danger',
      onOk: async () => {
        try {
          const response = await fetch(`/api/settings/restore-backup/${backupId}`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });

          if (response.ok) {
            message.success('恢复成功，请重新登录');
            localStorage.removeItem('token');
            window.location.href = '/login';
          }
        } catch (error) {
          message.error('恢复失败');
        }
      }
    });
  };

  // 推送设置
  const handlePushSettingsSave = async (values) => {
    setLoading(true);
    try {
      const response = await fetch('/api/settings/push-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(values)
      });

      if (response.ok) {
        message.success('推送设置保存成功');
        fetchPushSettings();
      } else {
        throw new Error('推送设置保存失败');
      }
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestPush = async () => {
    const values = pushForm.getFieldsValue();
    if (!values.webhook_url && !values.bark_url) {
      message.error('请至少配置一个推送渠道');
      return;
    }

    try {
      const response = await fetch('/api/settings/test-push', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(values)
      });

      if (response.ok) {
        message.success('测试推送发送成功');
      } else {
        throw new Error('测试推送失败');
      }
    } catch (error) {
      message.error(error.message);
    }
  };

  const backupColumns = [
    {
      title: '备份名称',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '文件大小',
      dataIndex: 'size',
      key: 'size',
      render: (size) => `${(size / 1024 / 1024).toFixed(2)} MB`
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => new Date(time).toLocaleString()
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Badge 
          status={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing'} 
          text={status === 'completed' ? '完成' : status === 'failed' ? '失败' : '进行中'} 
        />
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            icon={<DownloadOutlined />} 
            onClick={() => handleDownloadBackup(record.id)}
            disabled={record.status !== 'completed'}
          >
            下载
          </Button>
          <Button 
            type="link" 
            onClick={() => handleRestoreBackup(record.id)}
            disabled={record.status !== 'completed'}
          >
            恢复
          </Button>
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDeleteBackup(record.id)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2} className="page-title">系统设置</Title>
      
      <Tabs defaultActiveKey="password" type="card">
        <TabPane tab="密码修改" key="password">
          <Card className="hover-lift settings-card">
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handlePasswordChange}
              style={{ maxWidth: 400 }}
            >
              <Form.Item
                label="当前密码"
                name="old_password"
                rules={[{ required: true, message: '请输入当前密码' }]}
              >
                <Password placeholder="请输入当前密码" />
              </Form.Item>
              
              <Form.Item
                label="新密码"
                name="new_password"
                rules={[
                  { required: true, message: '请输入新密码' },
                  { min: 6, message: '密码长度至少6位' }
                ]}
              >
                <Password placeholder="请输入新密码" />
              </Form.Item>
              
              <Form.Item
                label="确认新密码"
                name="confirm_password"
                rules={[
                  { required: true, message: '请确认新密码' },
                  { min: 6, message: '密码长度至少6位' }
                ]}
              >
                <Password placeholder="请再次输入新密码" />
              </Form.Item>
              
              <Form.Item>
                <Button 
                  type="primary" 
                  icon={<SaveOutlined />} 
                  htmlType="submit"
                  loading={loading}
                >
                  修改密码
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab="数据备份" key="backup">
          <Card className="hover-lift settings-card">
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button 
                  type="primary" 
                  icon={<DownloadOutlined />} 
                  onClick={handleCreateBackup}
                  loading={loading}
                >
                  创建备份
                </Button>
                <Button 
                  icon={<ReloadOutlined />} 
                  onClick={fetchBackupHistory}
                >
                  刷新
                </Button>
              </Space>
            </div>
            
            <Table
              columns={backupColumns}
              dataSource={backupHistory}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="推送设置" key="push">
          <Card className="hover-lift settings-card">
            <Form
              form={pushForm}
              layout="vertical"
              onFinish={handlePushSettingsSave}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Title level={4}>Webhook 推送</Title>
                  <Form.Item label="启用状态" name="webhook_enabled" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                  
                  <Form.Item label="Webhook URL" name="webhook_url">
                    <Input placeholder="如: https://open.feishu.cn/open-apis/bot/v2/hook/xxx" />
                  </Form.Item>
                  
                  <Form.Item label="推送类型" name="webhook_types">
                    <Select mode="multiple" placeholder="选择推送类型">
                      <Option value="firewall_alert">防火墙告警</Option>
                      <Option value="system_alert">系统告警</Option>
                      <Option value="login_alert">登录告警</Option>
                      <Option value="backup_complete">备份完成</Option>
                    </Select>
                  </Form.Item>
                </Col>
                
                <Col span={12}>
                  <Title level={4}>Bark 推送</Title>
                  <Form.Item label="启用状态" name="bark_enabled" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                  
                  <Form.Item label="Bark URL" name="bark_url">
                    <Input placeholder="如: https://api.day.app/xxx/标题/内容" />
                  </Form.Item>
                  
                  <Form.Item label="推送类型" name="bark_types">
                    <Select mode="multiple" placeholder="选择推送类型">
                      <Option value="firewall_alert">防火墙告警</Option>
                      <Option value="system_alert">系统告警</Option>
                      <Option value="login_alert">登录告警</Option>
                      <Option value="backup_complete">备份完成</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider />
              
              <Form.Item>
                <Space>
                  <Button 
                    type="primary" 
                    icon={<SaveOutlined />} 
                    htmlType="submit"
                    loading={loading}
                  >
                    保存设置
                  </Button>
                                     <Button 
                     icon={<ExperimentOutlined />} 
                     onClick={handleTestPush}
                   >
                     测试推送
                   </Button>
                </Space>
              </Form.Item>
            </Form>
            
            <Alert
              message="推送说明"
              description="Webhook支持飞书、钉钉、企业微信等平台。Bark是iOS平台的推送服务，需要在iOS设备上安装Bark应用。"
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Settings;
