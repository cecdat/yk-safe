import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Switch,
  DatePicker,
  message,
  Space,
  Tag,
  Progress,
  Row,
  Col,
  Statistic,
  Typography,
  Select
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  ReloadOutlined,
  CopyOutlined,
  KeyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { CopyToClipboard } from 'react-copy-to-clipboard';
import dayjs from 'dayjs';
import axios from 'axios';

const { Title, Text } = Typography;
const { TextArea } = Input;

// 配置axios
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// 添加请求拦截器，自动添加认证token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 添加响应拦截器，处理认证错误
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      message.error('认证失败，请重新登录');
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

const TokenManagement = () => {
  const [loading, setLoading] = useState(false);
  const [tokens, setTokens] = useState([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [stats, setStats] = useState({});
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 获取token列表
  const fetchTokens = async (page, size) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: (page - 1) * size,
        limit: size,
      });

      const response = await api.get(`/tokens/?${params}`);
      setTokens(response.data.tokens || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      message.error('获取Token列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息
  const fetchStats = async () => {
    try {
      const response = await api.get('/tokens/stats/overview');
      setStats(response.data);
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  useEffect(() => {
    fetchTokens(currentPage, pageSize);
    fetchStats();
  }, [currentPage, pageSize]);

  // 创建token
  const handleCreateToken = async (values) => {
    try {
      const response = await api.post('/tokens/', {
        ...values,
      });

      if (response.status === 200 || response.status === 201) { // axios uses status for success
        const newToken = response.data;
        message.success('Token创建成功');
        setModalVisible(false);
        form.resetFields();
        fetchTokens(currentPage, pageSize);
        fetchStats();
        
        // 显示新创建的token
        Modal.success({
          title: 'Token创建成功',
          content: (
            <div>
              <p>Token已成功创建，请妥善保管以下信息：</p>
              <Text code copyable>{newToken.token}</Text>
            </div>
          ),
        });
      } else {
        const error = response.data;
        message.error(error.detail || '创建Token失败');
      }
    } catch (error) {
      message.error('创建Token失败');
    }
  };

  // 删除token
  const handleDeleteToken = async (tokenId) => {
    try {
      const response = await api.delete(`/tokens/${tokenId}`);

      if (response.status === 200 || response.status === 204) { // axios uses status for success
        message.success('Token删除成功');
        fetchTokens(currentPage, pageSize);
        fetchStats();
      } else {
        const error = response.data;
        message.error(error.detail || '删除Token失败');
      }
    } catch (error) {
      message.error('删除Token失败');
    }
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Token',
      dataIndex: 'token',
      key: 'token',
      width: 200,
      render: (token) => (
        <Space>
          <Text code style={{ fontSize: '12px' }}>
            {token.substring(0, 16)}...
          </Text>
          <CopyToClipboard text={token} onCopy={() => message.success('Token已复制')}>
            <Button type="text" size="small" icon={<CopyOutlined />} />
          </CopyToClipboard>
        </Space>
      ),
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 150,
    },
    {
      title: '使用情况',
      key: 'usage',
      width: 120,
      render: (_, record) => (
        <div>
          <div>{record.used_count}/{record.max_uses}</div>
          <Progress 
            percent={Math.round((record.used_count / record.max_uses) * 100)} 
            size="small" 
            status={record.used_count >= record.max_uses ? 'exception' : 'normal'}
          />
        </div>
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
             render: (_, record) => {
         return (
           <Space direction="vertical" size="small">
             <Tag color={record.is_active ? 'green' : 'red'}>
               {record.is_active ? '激活' : '禁用'}
             </Tag>
             <Tag color="blue">永久有效</Tag>
             {record.auto_approve && (
               <Tag color="orange">自动审批</Tag>
             )}
           </Space>
         );
       },
    },
    
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button 
            type="text" 
            size="small" 
            danger 
            icon={<DeleteOutlined />}
            onClick={() => {
              Modal.confirm({
                title: '确定要删除这个Token吗？',
                content: '删除后无法恢复，请谨慎操作。',
                onOk: () => handleDeleteToken(record.id),
              });
            }}
          />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总Token数"
              value={stats.total_tokens || 0}
              prefix={<KeyOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃Token"
              value={stats.active_tokens || 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="今日创建"
              value={stats.today_tokens || 0}
              prefix={<PlusOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={3}>Token管理</Title>
        <Space>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => setModalVisible(true)}
          >
            创建Token
          </Button>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              fetchTokens(currentPage, pageSize);
              fetchStats();
            }}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* Token列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={tokens}
          rowKey="id"
          loading={loading}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size);
            },
          }}
        />
      </Card>

      {/* 创建Token模态框 */}
      <Modal
        title="创建Token"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateToken}
        >
          <Form.Item
            name="company_name"
            label="公司名称"
            rules={[{ required: true, message: '请输入公司名称' }]}
          >
            <Input placeholder="请输入公司名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="请输入描述信息" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="max_uses"
                label="最大使用次数"
                rules={[{ required: true, message: '请输入最大使用次数' }]}
              >
                <InputNumber min={1} max={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="token_length"
                label="Token长度"
                initialValue={32}
              >
                <InputNumber min={16} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="是否激活"
                valuePropName="checked"
                initialValue={true}
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="auto_approve"
                label="自动审批"
                valuePropName="checked"
                initialValue={true}
                hidden={true}  // 隐藏自动审批选项，因为所有token都是自动审批的
              >
                <Switch disabled={true} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建
              </Button>
              <Button onClick={() => {
                setModalVisible(false);
                form.resetFields();
              }}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TokenManagement;
