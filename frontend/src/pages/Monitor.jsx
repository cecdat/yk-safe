import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Space, Button, Modal, message, Descriptions, Divider } from 'antd';
import {
  ReloadOutlined,
  GlobalOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { getNetworkInfo, getNetworkConnections } from '../api/monitor';



const Monitor = () => {
  const [loading, setLoading] = useState(false);
  const [networkData, setNetworkData] = useState({});
  const [connectionModalVisible, setConnectionModalVisible] = useState(false);
  const [connectionDetails, setConnectionDetails] = useState([]);

  const fetchMonitorData = async () => {
    setLoading(true);
    try {
      const networkRes = await getNetworkInfo();
      setNetworkData(networkRes.data?.data || {});
    } catch (error) {
      console.error('Monitor data fetch error:', error);
      message.error('获取网络监控数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitorData();
    // 每10秒刷新一次数据
    const interval = setInterval(fetchMonitorData, 10000);
    return () => clearInterval(interval);
  }, []);










  // 网络连接表格列定义
  const connectionColumns = [
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (text, record) => (
        <Space direction="vertical" size="small">
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          {record.location && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              <EnvironmentOutlined /> {record.location.summary || '位置未知'}
            </div>
          )}
        </Space>
      ),
    },
    {
      title: '地理位置',
      dataIndex: 'location',
      key: 'location',
      render: (location) => {
        if (!location) return '未知';
        return (
          <Space direction="vertical" size="small">
            <div>{location.country}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {location.city} {location.region && `· ${location.region}`}
            </div>
            {location.timezone && (
              <div style={{ fontSize: '11px', color: '#999' }}>
                <ClockCircleOutlined /> {location.timezone}
              </div>
            )}
          </Space>
        );
      },
    },
    {
      title: '连接数',
      dataIndex: 'connection_count',
      key: 'connection_count',
      render: (count) => (
        <Tag color={count > 10 ? 'red' : count > 5 ? 'orange' : 'green'}>
          {count}
        </Tag>
      ),
    },
    {
      title: '连接详情',
      dataIndex: 'connections',
      key: 'connections',
      render: (connections) => {
        if (!connections || connections.length === 0) return '无';
        return (
          <Space direction="vertical" size="small">
            {connections.slice(0, 3).map((conn, index) => (
              <div key={index} style={{ fontSize: '12px' }}>
                <code>{conn.local_address}</code> → <code>{conn.remote_address}</code>
                <Tag size="small" color={conn.status === 'ESTABLISHED' ? 'green' : 'orange'} style={{ marginLeft: 4 }}>
                  {conn.status}
                </Tag>
              </div>
            ))}
            {connections.length > 3 && (
              <div style={{ fontSize: '11px', color: '#999' }}>
                还有 {connections.length - 3} 个连接...
              </div>
            )}
          </Space>
        );
      },
    },
  ];

  // 处理网络连接点击事件
  const handleConnectionsClick = async () => {
    setLoading(true);
    try {
      const res = await getNetworkConnections();
      const data = res.data?.data;
      if (data) {
        setConnectionDetails(data.connections || []);
        setConnectionModalVisible(true);
      }
    } catch (error) {
      console.error('Network connections fetch error:', error);
      message.error('获取网络连接详情失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>网络监控</h2>
        <Button 
          type="primary" 
          icon={<ReloadOutlined />} 
          onClick={fetchMonitorData}
          loading={loading}
        >
          刷新数据
        </Button>
      </div>

      {/* 网络连接概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Statistic
              title="网络连接"
              value={networkData.connections?.total || 0}
              prefix={<GlobalOutlined />}
              valueStyle={{ color: '#722ed1', cursor: 'pointer' }}
              onClick={handleConnectionsClick}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666', cursor: 'pointer' }} onClick={handleConnectionsClick}>
              点击查看详情 →
            </div>
          </Card>
        </Col>
      </Row>







      {/* 网络连接详情弹窗 */}
      <Modal
        title={
          <Space>
            <GlobalOutlined />
            网络连接详情
          </Space>
        }
        open={connectionModalVisible}
        onCancel={() => setConnectionModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setConnectionModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={1200}
      >
        {connectionDetails.length > 0 && (
          <>
            <Descriptions title="连接统计" bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="总连接数">
                <Tag color="blue">{connectionDetails.reduce((sum, item) => sum + item.connection_count, 0)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="唯一IP数">
                <Tag color="green">{connectionDetails.length}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="最多连接IP">
                {connectionDetails[0] && (
                  <Tag color="red">
                    {connectionDetails[0].ip} ({connectionDetails[0].connection_count})
                  </Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
            <Divider />
          </>
        )}
        
        <Table
          columns={connectionColumns}
          dataSource={connectionDetails}
          rowKey="ip"
          pagination={{ 
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
          }}
          size="small"
          loading={loading}
          scroll={{ x: 1000 }}
        />
        
        {connectionDetails.length === 0 && (
          <div style={{ textAlign: 'center', color: '#999', padding: '40px 0' }}>
            暂无连接信息
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Monitor;
