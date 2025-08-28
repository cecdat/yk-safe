import React from 'react';
import { Card, Table, Button, Space, Tag, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';

const WhitelistTokens = () => {
  const [loading, setLoading] = React.useState(false);
  const [tokens, setTokens] = React.useState([]);

  const fetchTokens = async () => {
    setLoading(true);
    try {
      // 临时使用模拟数据
      setTokens([]);
      message.info('Token管理功能开发中...');
    } catch (error) {
      message.error('获取Token列表失败');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchTokens();
  }, []);

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
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (active) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? '激活' : '禁用'}
        </Tag>
      )
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>白名单Token管理</h2>
        <Space>
          <Button 
            type="primary" 
            icon={<PlusOutlined />} 
            onClick={() => message.info('创建Token功能开发中...')}
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
          columns={columns}
          dataSource={tokens}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
};

export default WhitelistTokens;
