import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, InputNumber, DatePicker, message, Tabs } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { getWhitelistTokens, createWhitelistToken, updateWhitelistToken, deleteWhitelistToken, getWhitelistRequests, approveWhitelistRequest } from '../api/whitelist';
import dayjs from 'dayjs';

const { Option } = Select;
const { TabPane } = Tabs;

const WhitelistManagement = () => {
  const [loading, setLoading] = useState(false);
  const [tokens, setTokens] = useState([]);
  const [requests, setRequests] = useState([]);
  const [tokenModalVisible, setTokenModalVisible] = useState(false);
  const [editingToken, setEditingToken] = useState(null);
  const [tokenForm] = Form.useForm();

  const fetchTokens = async () => {
    setLoading(true);
    try {
      const response = await getWhitelistTokens();
      setTokens(response.data || []);
    } catch (error) {
      message.error('获取Token列表失败');
      console.error('Fetch tokens error:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRequests = async () => {
    setLoading(true);
    try {
      const response = await getWhitelistRequests();
      setRequests(response.data || []);
    } catch (error) {
      message.error('获取申请列表失败');
      console.error('Fetch requests error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTokens();
    fetchRequests();
  }, []);

  const handleCreateToken = async (values) => {
    try {
      await createWhitelistToken({
        ...values,
        expires_at: values.expires_at.toISOString()
      });
      message.success('创建Token成功');
      setTokenModalVisible(false);
      tokenForm.resetFields();
      fetchTokens();
    } catch (error) {
      message.error('创建Token失败');
      console.error('Create token error:', error);
    }
  };

  const handleUpdateToken = async (values) => {
    try {
      await updateWhitelistToken(editingToken.id, {
        ...values,
        expires_at: values.expires_at?.toISOString()
      });
      message.success('更新Token成功');
      setTokenModalVisible(false);
      setEditingToken(null);
      tokenForm.resetFields();
      fetchTokens();
    } catch (error) {
      message.error('更新Token失败');
      console.error('Update token error:', error);
    }
  };

  const handleDeleteToken = async (tokenId) => {
    try {
      await deleteWhitelistToken(tokenId);
      message.success('删除Token成功');
      fetchTokens();
    } catch (error) {
      message.error('删除Token失败');
      console.error('Delete token error:', error);
    }
  };

  const handleApproveRequest = async (requestId, status) => {
    try {
      await approveWhitelistRequest(requestId, {
        status,
        approved_by: 'admin'
      });
      message.success(`申请${status === 'approved' ? '通过' : '拒绝'}成功`);
      fetchRequests();
    } catch (error) {
      message.error('操作失败');
      console.error('Approve request error:', error);
    }
  };

  const tokenColumns = [
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
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {token.substring(0, 8)}...
        </span>
      )
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 150,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '使用次数',
      key: 'usage',
      width: 120,
      render: (_, record) => (
        <span>{record.used_count} / {record.max_uses}</span>
      )
    },
    {
      title: '过期时间',
      dataIndex: 'expires_at',
      key: 'expires_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (active) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '激活' : '禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingToken(record);
              tokenForm.setFieldsValue({
                ...record,
                expires_at: dayjs(record.expires_at)
              });
              setTokenModalVisible(true);
            }}
          >
            编辑
          </Button>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteToken(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  const requestColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '公司名称',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 150,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 120,
    },
    {
      title: '代理状态',
      dataIndex: 'is_proxy',
      key: 'is_proxy',
      width: 100,
      render: (isProxy) => (
        <Tag color={isProxy ? 'orange' : 'green'}>
          {isProxy ? '代理' : '直连'}
        </Tag>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const colors = {
          pending: 'orange',
          approved: 'green',
          rejected: 'red'
        };
        const texts = {
          pending: '待审核',
          approved: '已通过',
          rejected: '已拒绝'
        };
        return <Tag color={colors[status]}>{texts[status]}</Tag>;
      }
    },
    {
      title: '申请时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="middle">
          {record.status === 'pending' && (
            <>
              <Button
                type="text"
                icon={<CheckOutlined />}
                onClick={() => handleApproveRequest(record.id, 'approved')}
              >
                通过
              </Button>
              <Button
                type="text"
                danger
                icon={<CloseOutlined />}
                onClick={() => handleApproveRequest(record.id, 'rejected')}
              >
                拒绝
              </Button>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Tabs defaultActiveKey="tokens">
        <TabPane tab="Token管理" key="tokens">
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>白名单Token管理</h2>
            <Space>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={() => {
                  setEditingToken(null);
                  tokenForm.resetFields();
                  setTokenModalVisible(true);
                }}
              >
                创建Token
              </Button>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={fetchTokens}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </div>

          <Card>
            <Table
              columns={tokenColumns}
              dataSource={tokens}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab="申请管理" key="requests">
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>白名单申请管理</h2>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchRequests}
              loading={loading}
            >
              刷新
            </Button>
          </div>

          <Card>
            <Table
              columns={requestColumns}
              dataSource={requests}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      <Modal
        title={editingToken ? "编辑Token" : "创建Token"}
        open={tokenModalVisible}
        onCancel={() => {
          setTokenModalVisible(false);
          setEditingToken(null);
          tokenForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={tokenForm}
          layout="vertical"
          onFinish={editingToken ? handleUpdateToken : handleCreateToken}
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
            <Input.TextArea placeholder="请输入Token描述" rows={3} />
          </Form.Item>

          <Form.Item
            name="max_uses"
            label="最大使用次数"
            rules={[{ required: true, message: '请输入最大使用次数' }]}
          >
            <InputNumber min={1} max={10000} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="expires_at"
            label="过期时间"
            rules={[{ required: true, message: '请选择过期时间' }]}
          >
            <DatePicker 
              showTime 
              style={{ width: '100%' }} 
              placeholder="请选择过期时间"
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingToken ? '更新' : '创建'}
              </Button>
              <Button onClick={() => {
                setTokenModalVisible(false);
                setEditingToken(null);
                tokenForm.resetFields();
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

export default WhitelistManagement;
