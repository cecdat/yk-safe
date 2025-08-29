import React, { useState, useEffect } from 'react';
import {
  Card,
  Select,
  Form,
  Input,
  Button,
  Space,
  Table,
  Modal,
  message,
  Row,
  Col,
  Typography,
  Divider,
  Tag,
  Progress,
  Alert
} from 'antd';
import {
  DownloadOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const NetworkTools = () => {
  const [activeTool, setActiveTool] = useState('tcpdump');
  const [form] = Form.useForm();
  const [captureHistory, setCaptureHistory] = useState([]);
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureProgress, setCaptureProgress] = useState(0);
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState(null);

  // 获取网卡列表
  const [interfaces, setInterfaces] = useState([]);

  useEffect(() => {
    fetchInterfaces();
    fetchCaptureHistory();
  }, []);

  const fetchInterfaces = async () => {
    try {
      const response = await fetch('/api/network/interfaces', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setInterfaces(data.data || []);
      }
    } catch (error) {
      console.error('获取网卡列表失败:', error);
    }
  };

  const fetchCaptureHistory = async () => {
    try {
      const response = await fetch('/api/network/capture-history', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setCaptureHistory(data.data || []);
      }
    } catch (error) {
      console.error('获取抓包历史失败:', error);
    }
  };

  const handleToolChange = (value) => {
    setActiveTool(value);
    setOutput('');
    setIsRunning(false);
    setCurrentTask(null);
    form.resetFields();
  };

  const handleStartCapture = async (values) => {
    if (activeTool !== 'tcpdump') return;

    setIsCapturing(true);
    setCaptureProgress(0);
    setOutput('开始抓包...\n');

    try {
      const response = await fetch('/api/network/start-capture', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          ...values,
          duration: parseInt(values.duration) || 60
        })
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentTask(data.data.task_id);
        
        // 开始轮询进度
        pollCaptureProgress(data.data.task_id);
      } else {
        throw new Error('启动抓包失败');
      }
    } catch (error) {
      message.error('启动抓包失败: ' + error.message);
      setIsCapturing(false);
    }
  };

  const pollCaptureProgress = async (taskId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/network/capture-status/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          const status = data.data;

          setCaptureProgress(status.progress);
          setOutput(prev => prev + status.output + '\n');

          if (status.status === 'completed') {
            setIsCapturing(false);
            setCurrentTask(null);
            clearInterval(interval);
            message.success('抓包完成');
            fetchCaptureHistory();
          } else if (status.status === 'failed') {
            setIsCapturing(false);
            setCurrentTask(null);
            clearInterval(interval);
            message.error('抓包失败: ' + status.error);
          }
        }
      } catch (error) {
        console.error('轮询进度失败:', error);
      }
    }, 1000);
  };

  const handleStopCapture = async () => {
    if (!currentTask) return;

    try {
      const response = await fetch(`/api/network/stop-capture/${currentTask}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        setIsCapturing(false);
        setCurrentTask(null);
        message.success('已停止抓包');
      }
    } catch (error) {
      message.error('停止抓包失败');
    }
  };

  const handleStopCommand = async () => {
    if (!currentTask) return;

    try {
      let endpoint = '';
      if (activeTool === 'ping') {
        endpoint = `/api/network/stop-ping/${currentTask}`;
      } else if (activeTool === 'traceroute') {
        endpoint = `/api/network/stop-traceroute/${currentTask}`;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        message.success('命令已停止');
        setIsRunning(false);
        setCurrentTask(null);
      }
    } catch (error) {
      message.error('停止命令失败');
    }
  };

  const handleDownload = async (fileId) => {
    try {
      const response = await fetch(`/api/network/download/${fileId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `capture_${fileId}.pcap.gz`;
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

  const handleDeleteCapture = async (fileId) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个抓包文件吗？',
      onOk: async () => {
        try {
          const response = await fetch(`/api/network/delete-capture/${fileId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });

          if (response.ok) {
            message.success('删除成功');
            fetchCaptureHistory();
          }
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const handleRunCommand = async (values) => {
    if (activeTool === 'tcpdump') return;

    setIsRunning(true);
    setOutput('执行命令...\n');

    try {
      let endpoint = '';
      if (activeTool === 'ping') {
        endpoint = `/api/network/start-ping?target=${encodeURIComponent(values.target)}`;
      } else if (activeTool === 'traceroute') {
        endpoint = `/api/network/start-traceroute?target=${encodeURIComponent(values.target)}`;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentTask(data.data.task_id);
        
        // 开始轮询输出
        pollCommandOutput(data.data.task_id);
      } else {
        throw new Error('执行命令失败');
      }
    } catch (error) {
      message.error('执行命令失败: ' + error.message);
      setIsRunning(false);
    }
  };

  const pollCommandOutput = async (taskId) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/network/task-status/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          const status = data.data;

          setOutput(status.output || '执行中...');

          if (status.status === 'completed' || status.status === 'failed') {
            setIsRunning(false);
            setCurrentTask(null);
            clearInterval(interval);
            
            if (status.status === 'failed') {
              message.error('命令执行失败: ' + (status.error_message || '未知错误'));
            }
          }
        }
      } catch (error) {
        console.error('轮询输出失败:', error);
      }
    }, 1000);
  };

  const renderTcpdumpForm = () => (
    <Form form={form} layout="vertical" onFinish={handleStartCapture}>
      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="协议" name="protocol">
            <Select placeholder="选择协议" allowClear>
              <Option value="tcp">TCP</Option>
              <Option value="udp">UDP</Option>
              <Option value="icmp">ICMP</Option>
              <Option value="all">全部</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="网卡" name="interface" rules={[{ required: true, message: '请选择网卡' }]}>
            <Select placeholder="选择网卡">
              {interfaces.map(iface => (
                <Option key={iface.name} value={iface.name}>
                  {iface.name} ({iface.ip})
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="抓包时长(秒)" name="duration" rules={[{ required: true, message: '请输入抓包时长' }]}>
            <Input type="number" min="1" max="3600" placeholder="60" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="源IP" name="source_ip">
            <Input placeholder="可选，如: 192.168.1.1" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="目标IP" name="target_ip">
            <Input placeholder="可选，如: 8.8.8.8" />
          </Form.Item>
        </Col>
      </Row>
      <Form.Item>
        <Space>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />} 
            onClick={() => form.submit()}
            loading={isCapturing}
            disabled={isCapturing}
          >
            开始抓包
          </Button>
          {isCapturing && (
            <Button 
              danger 
              icon={<StopOutlined />} 
              onClick={handleStopCapture}
            >
              停止抓包
            </Button>
          )}
        </Space>
      </Form.Item>
    </Form>
  );

  const renderPingForm = () => (
    <Form form={form} layout="vertical" onFinish={handleRunCommand}>
      <Form.Item label="目标IP" name="target" rules={[{ required: true, message: '请输入目标IP' }]}>
        <Input placeholder="如: 8.8.8.8" />
      </Form.Item>
      <Form.Item>
        <Space>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />} 
            onClick={() => form.submit()}
            loading={isRunning}
            disabled={isRunning}
          >
            开始Ping
          </Button>
          {isRunning && (
            <Button 
              danger
              icon={<StopOutlined />} 
              onClick={handleStopCommand}
            >
              停止
            </Button>
          )}
        </Space>
      </Form.Item>
    </Form>
  );

  const renderTracerouteForm = () => (
    <Form form={form} layout="vertical" onFinish={handleRunCommand}>
      <Form.Item label="目标IP" name="target" rules={[{ required: true, message: '请输入目标IP' }]}>
        <Input placeholder="如: 8.8.8.8" />
      </Form.Item>
      <Form.Item>
        <Space>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />} 
            onClick={() => form.submit()}
            loading={isRunning}
            disabled={isRunning}
          >
            开始路由追踪
          </Button>
          {isRunning && (
            <Button 
              danger
              icon={<StopOutlined />} 
              onClick={handleStopCommand}
            >
              停止
            </Button>
          )}
        </Space>
      </Form.Item>
    </Form>
  );

  const captureColumns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol',
      render: (protocol) => <Tag color="blue">{protocol}</Tag>
    },
    {
      title: '网卡',
      dataIndex: 'interface',
      key: 'interface',
    },
    {
      title: '文件大小',
      dataIndex: 'size',
      key: 'size',
      render: (size) => `${(size / 1024).toFixed(2)} KB`
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="link" 
            icon={<DownloadOutlined />} 
            onClick={() => handleDownload(record.id)}
          >
            下载
          </Button>
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDeleteCapture(record.id)}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2} className="page-title">网络工具</Title>
      
      <Card style={{ marginBottom: 24 }} className="hover-lift tool-card">
        <Form.Item label="选择工具">
          <Select 
            value={activeTool} 
            onChange={handleToolChange}
            style={{ width: 200 }}
          >
            <Option value="tcpdump">TCPDump 抓包</Option>
            <Option value="ping">Ping 测试</Option>
            <Option value="traceroute">路由追踪</Option>
          </Select>
        </Form.Item>

        <Divider />

        {activeTool === 'tcpdump' && renderTcpdumpForm()}
        {activeTool === 'ping' && renderPingForm()}
        {activeTool === 'traceroute' && renderTracerouteForm()}
      </Card>

      {(isCapturing || isRunning) && (
        <Card style={{ marginBottom: 24 }} className="hover-lift tool-card">
          <Title level={4}>执行状态</Title>
          {isCapturing && (
            <div style={{ marginBottom: 16 }}>
              <Text>抓包进度: </Text>
              <Progress percent={captureProgress} status="active" />
            </div>
          )}
          <TextArea
            value={output}
            rows={10}
            readOnly
            placeholder="命令输出将在这里显示..."
          />
        </Card>
      )}

      {activeTool === 'tcpdump' && (
        <Card className="hover-lift tool-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <Title level={4}>抓包历史</Title>
            <Button icon={<ReloadOutlined />} onClick={fetchCaptureHistory}>
              刷新
            </Button>
          </div>
          <Table
            columns={captureColumns}
            dataSource={captureHistory}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}
    </div>
  );
};

export default NetworkTools;
