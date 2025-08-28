import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Tag, 
  Space, 
  Button, 
  Select, 
  DatePicker, 
  Form, 
  Row, 
  Col,
  Statistic,
  Tabs
} from 'antd';
import { 
  ReloadOutlined, 
  FileTextOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { getSystemLogs, getFirewallLogs, getLogStats } from '../api/firewall';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

const Logs = () => {
  const [loading, setLoading] = useState(false);
  const [systemLogs, setSystemLogs] = useState([]);
  const [firewallLogs, setFirewallLogs] = useState([]);
  const [logStats, setLogStats] = useState({});
  const [filters, setFilters] = useState({
    level: '',
    source: '',
    action: '',
    protocol: '',
    days: 7
  });
  const [form] = Form.useForm();

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const [systemRes, firewallRes, statsRes] = await Promise.all([
        getSystemLogs(filters),
        getFirewallLogs(filters),
        getLogStats()
      ]);

      setSystemLogs(Array.isArray(systemRes.data) ? systemRes.data : []);
      setFirewallLogs(Array.isArray(firewallRes.data) ? firewallRes.data : []);
      setLogStats(statsRes.data || {});
    } catch (error) {
      console.error('Logs fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const handleFilterChange = (changedValues) => {
    setFilters(prev => ({ ...prev, ...changedValues }));
  };

  const systemLogColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss')
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      render: (level) => {
        const color = level === 'error' ? 'red' : level === 'warning' ? 'orange' : 'green';
        const icon = level === 'error' ? <ExclamationCircleOutlined /> : 
                    level === 'warning' ? <InfoCircleOutlined /> : <CheckCircleOutlined />;
        return <Tag color={color} icon={icon}>{level.toUpperCase()}</Tag>;
      }
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      render: (source) => <Tag>{source}</Tag>
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true
    }
  ];

  const firewallLogColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text) => dayjs(text).format('YYYY-MM-DD HH:mm:ss')
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      render: (action) => (
        <Tag color={action === 'accept' ? 'green' : 'red'}>
          {action === 'accept' ? '允许' : '拒绝'}
        </Tag>
      )
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol',
      render: (protocol) => <Tag color="blue">{protocol}</Tag>
    },
    {
      title: '源地址',
      dataIndex: 'source_ip',
      key: 'source_ip',
    },
    {
      title: '目标地址',
      dataIndex: 'destination_ip',
      key: 'destination_ip',
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>系统日志</h2>
        <Button 
          type="primary" 
          icon={<ReloadOutlined />} 
          onClick={fetchLogs}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      {/* 日志统计 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总日志数"
              value={logStats.total_logs || 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="错误日志"
              value={logStats.error_logs || 0}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="警告日志"
              value={logStats.warning_logs || 0}
              valueStyle={{ color: '#faad14' }}
              prefix={<InfoCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="信息日志"
              value={logStats.info_logs || 0}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 过滤器 */}
      <Card style={{ marginBottom: 16 }}>
        <Form
          form={form}
          layout="inline"
          onValuesChange={handleFilterChange}
        >
          <Form.Item name="level" label="日志级别">
            <Select placeholder="选择级别" style={{ width: 120 }} allowClear>
              <Option value="error">错误</Option>
              <Option value="warning">警告</Option>
              <Option value="info">信息</Option>
            </Select>
          </Form.Item>
          <Form.Item name="source" label="日志来源">
            <Select placeholder="选择来源" style={{ width: 120 }} allowClear>
              <Option value="firewall">防火墙</Option>
              <Option value="blacklist">黑名单</Option>
              <Option value="system">系统</Option>
            </Select>
          </Form.Item>
          <Form.Item name="action" label="动作">
            <Select placeholder="选择动作" style={{ width: 120 }} allowClear>
              <Option value="accept">允许</Option>
              <Option value="drop">拒绝</Option>
            </Select>
          </Form.Item>
          <Form.Item name="protocol" label="协议">
            <Select placeholder="选择协议" style={{ width: 120 }} allowClear>
              <Option value="tcp">TCP</Option>
              <Option value="udp">UDP</Option>
              <Option value="icmp">ICMP</Option>
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* 日志内容 */}
      <Tabs defaultActiveKey="system">
        <TabPane tab="系统日志" key="system">
          <Table
            columns={systemLogColumns}
            dataSource={systemLogs}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 50 }}
            scroll={{ x: 800 }}
          />
        </TabPane>
        <TabPane tab="防火墙日志" key="firewall">
          <Table
            columns={firewallLogColumns}
            dataSource={firewallLogs}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 50 }}
            scroll={{ x: 1000 }}
          />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Logs;
