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
  const [captureTimeLeft, setCaptureTimeLeft] = useState(0);
  const [captureDataSize, setCaptureDataSize] = useState(0);
  const [output, setOutput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState(null);

  // 获取网卡列表
  const [interfaces, setInterfaces] = useState([]);

  useEffect(() => {
    fetchInterfaces();
    fetchCaptureHistory();
    
    // 页面刷新或组件卸载时清理状态
    const handleBeforeUnload = () => {
      setOutput('');
      setIsRunning(false);
      setIsCapturing(false);
      setCurrentTask(null);
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // 组件卸载时清理状态
      setOutput('');
      setIsRunning(false);
      setIsCapturing(false);
      setCurrentTask(null);
    };
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
        console.log('抓包历史数据:', data.data);
        setCaptureHistory(data.data || []);
      }
    } catch (error) {
      console.error('获取抓包历史失败:', error);
    }
  };

  const handleToolChange = (value) => {
    setActiveTool(value);
    // 只有在切换到抓包工具时才清空输出
    if (value === 'tcpdump') {
      setOutput('');
    }
    setIsRunning(false);
    setCurrentTask(null);
    form.resetFields();
  };

  const handleInterfaceChange = (value) => {
    // 当网卡选择改变时，更新表单中的IP显示
    const iface = interfaces.find(i => i.name === value);
    if (iface) {
      form.setFieldsValue({ selected_interface_ip: iface.ip });
    }
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
    const startTime = Date.now();
    const duration = form.getFieldValue('duration') || 60;
    
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

          // 计算倒计时和进度
          const elapsed = Math.floor((Date.now() - startTime) / 1000);
          const timeLeft = Math.max(0, duration - elapsed);
          setCaptureTimeLeft(timeLeft);
          
          // 修复进度计算：基于已用时间计算进度百分比
          const progress = Math.min(100, Math.max(0, (elapsed / duration) * 100));
          setCaptureProgress(progress);
          
          // 设置数据量（模拟，实际应该从后端获取）
          setCaptureDataSize(elapsed * 1024); // 假设每秒1KB数据
          
          // 使用后端返回的输出信息
          if (status.output) {
            setOutput(prev => {
              // 避免重复输出
              if (!prev.includes(status.output)) {
                return prev + status.output + '\n';
              }
              return prev;
            });
          }

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
            message.error('抓包失败: ' + (status.error_message || '未知错误'));
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
        // 不清空currentTask，保持执行状态卡片显示
        // 不清空输出，保留已执行的结果
        setOutput(prev => prev + '\n[命令已手动停止]\n');
        
        // 强制停止轮询
        if (window.currentPollingInterval) {
          clearInterval(window.currentPollingInterval);
          window.currentPollingInterval = null;
        }
      }
    } catch (error) {
      message.error('停止命令失败');
    }
  };

  const handleDownload = async (fileId) => {
    try {
      console.log('开始下载文件，task_id:', fileId);
      
      const response = await fetch(`/api/network/download-capture/${fileId}`, {
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
      } else {
        const errorData = await response.json();
        console.error('下载失败:', errorData);
        message.error('下载失败: ' + (errorData.detail || '未知错误'));
      }
    } catch (error) {
      console.error('下载出错:', error);
      message.error('下载失败: ' + error.message);
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

    // 如果正在运行，先停止之前的命令
    if (isRunning && currentTask) {
      await handleStopCommand();
      // 等待一下再开始新命令
      setTimeout(() => {
        startNewCommand(values);
      }, 100);
      return;
    }

    // 开始新命令时清空之前的输出和状态
    setOutput('执行命令...\n');
    setCurrentTask(null);
    startNewCommand(values);
  };

  const startNewCommand = async (values) => {
    setIsRunning(true);
    // 输出已经在handleRunCommand中清空

    try {
      let endpoint = '';
      let body = {};
      
      if (activeTool === 'ping') {
        endpoint = '/api/network/start-ping';
        body = { target: values.target };
      } else if (activeTool === 'traceroute') {
        endpoint = '/api/network/start-traceroute';
        body = { target: values.target };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(body)
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
    let isStopped = false;
    
    const interval = setInterval(async () => {
      // 如果已经停止，不再轮询
      if (isStopped) {
        clearInterval(interval);
        return;
      }
      
      try {
        const response = await fetch(`/api/network/task-status/${taskId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          const status = data.data;

          // 累积输出，而不是覆盖
          if (status.output && status.output.trim()) {
            setOutput(prev => {
              // 避免重复输出
              if (!prev.includes(status.output.trim())) {
                return prev + status.output + '\n';
              }
              return prev;
            });
          }

          if (status.status === 'completed' || status.status === 'failed') {
            isStopped = true;
            setIsRunning(false);
            // 不清空currentTask，保持执行状态卡片显示
            clearInterval(interval);
            
            // 只在真正失败时显示错误，停止命令不算失败
            if (status.status === 'failed' && status.error_message && 
                !status.error_message.includes('stopped') && 
                !status.error_message.includes('Ping失败') && 
                !status.error_message.includes('路由追踪失败')) {
              message.error('命令执行失败: ' + status.error_message);
            }
          }
        }
      } catch (error) {
        console.error('轮询输出失败:', error);
      }
    }, 1000);
    
    // 返回清理函数
    return () => {
      isStopped = true;
      clearInterval(interval);
    };
  };

  const renderTcpdumpForm = () => (
    <Form form={form} layout="horizontal" onFinish={handleStartCapture} size="small">
      <Row gutter={12}>
        <Col span={6}>
          <Form.Item label="协议" name="protocol" style={{ marginBottom: '8px' }}>
            <Select placeholder="协议" allowClear size="small">
              <Option value="tcp">TCP</Option>
              <Option value="udp">UDP</Option>
              <Option value="icmp">ICMP</Option>
              <Option value="all">全部</Option>
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="网卡" name="interface" rules={[{ required: true, message: '请选择网卡' }]} style={{ marginBottom: '8px' }}>
            <Select placeholder="选择网卡" onChange={handleInterfaceChange} size="small">
              {interfaces.map(iface => (
                <Option key={iface.name} value={iface.name}>
                  {iface.name} ({iface.ip})
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="时长(秒)" name="duration" rules={[{ required: true, message: '请输入抓包时长' }]} style={{ marginBottom: '8px' }}>
            <Input type="number" min="1" max="3600" placeholder="60" size="small" />
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item label="操作" style={{ marginBottom: '8px' }}>
            <Space size="small">
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />} 
                onClick={() => form.submit()}
                loading={isCapturing}
                disabled={isCapturing}
                size="small"
              >
                开始
              </Button>
              {isCapturing && (
                <Button 
                  danger 
                  icon={<StopOutlined />} 
                  onClick={handleStopCapture}
                  size="small"
                >
                  停止
                </Button>
              )}
            </Space>
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={12}>
        <Col span={12}>
          <Form.Item label="源IP" name="source_ip" style={{ marginBottom: '8px' }}>
            <Input placeholder="可选，如: 192.168.1.1" size="small" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="目标IP" name="target_ip" style={{ marginBottom: '8px' }}>
            <Input placeholder="可选，如: 8.8.8.8" size="small" />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  const renderPingForm = () => (
    <Form form={form} layout="horizontal" onFinish={handleRunCommand} size="small">
      <Row gutter={12} align="middle">
        <Col span={12}>
          <Form.Item label="目标IP" name="target" rules={[{ required: true, message: '请输入目标IP' }]} style={{ marginBottom: '8px' }}>
            <Input placeholder="如: 8.8.8.8" size="small" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="操作" style={{ marginBottom: '8px' }}>
            <Space size="small">
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />} 
                onClick={() => form.submit()}
                loading={isRunning}
                disabled={isRunning}
                size="small"
              >
                开始Ping
              </Button>
              {isRunning && (
                <Button 
                  danger
                  icon={<StopOutlined />} 
                  onClick={handleStopCommand}
                  size="small"
                >
                  停止
                </Button>
              )}
            </Space>
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );

  const renderTracerouteForm = () => (
    <Form form={form} layout="horizontal" onFinish={handleRunCommand} size="small">
      <Row gutter={12} align="middle">
        <Col span={12}>
          <Form.Item label="目标IP" name="target" rules={[{ required: true, message: '请输入目标IP' }]} style={{ marginBottom: '8px' }}>
            <Input placeholder="如: 8.8.8.8" size="small" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="操作" style={{ marginBottom: '8px' }}>
            <Space size="small">
              <Button 
                type="primary" 
                icon={<PlayCircleOutlined />} 
                onClick={() => form.submit()}
                loading={isRunning}
                disabled={isRunning}
                size="small"
              >
                开始路由追踪
              </Button>
              {isRunning && (
                <Button 
                  danger
                  icon={<StopOutlined />} 
                  onClick={handleStopCommand}
                  size="small"
                >
                  停止
                </Button>
              )}
            </Space>
          </Form.Item>
        </Col>
      </Row>
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
      render: (iface) => <Tag color="green">{iface}</Tag>
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size) => size ? `${(size / 1024).toFixed(2)} KB` : '未知'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const color = status === 'completed' ? 'success' : status === 'running' ? 'processing' : 'error';
        return <Tag color={color}>{status === 'completed' ? '完成' : status === 'running' ? '运行中' : '失败'}</Tag>
      }
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
            onClick={() => {
              console.log('点击下载按钮，record:', record);
              handleDownload(record.task_id);
            }}
            disabled={record.status !== 'completed'}
          >
            下载
          </Button>
          <Button 
            type="link" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => {
              console.log('点击删除按钮，record:', record);
              handleDeleteCapture(record.task_id);
            }}
          >
            删除
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '16px' }}>
      <Title level={3} className="page-title" style={{ marginBottom: '16px' }}>网络工具</Title>
      
      <Card 
        size="small" 
        style={{ marginBottom: '16px' }} 
        className="hover-lift tool-card"
        bodyStyle={{ padding: '16px' }}
      >
        <Row gutter={16} align="middle">
          <Col span={6}>
            <Form.Item label="选择工具" style={{ marginBottom: '8px' }}>
              <Select 
                value={activeTool} 
                onChange={handleToolChange}
                style={{ width: '100%' }}
                size="small"
              >
                <Option value="tcpdump">TCPDump 抓包</Option>
                <Option value="ping">Ping 测试</Option>
                <Option value="traceroute">路由追踪</Option>
              </Select>
            </Form.Item>
          </Col>
          <Col span={18}>
            {activeTool === 'tcpdump' && renderTcpdumpForm()}
            {activeTool === 'ping' && renderPingForm()}
            {activeTool === 'traceroute' && renderTracerouteForm()}
          </Col>
        </Row>
      </Card>

             {(isCapturing || isRunning) && (
         <Card 
           size="small" 
           style={{ marginBottom: '16px' }} 
           className="hover-lift tool-card"
           bodyStyle={{ padding: '16px' }}
         >
           <Title level={4} style={{ marginBottom: '12px' }}>执行状态</Title>
                       {isCapturing && (
              <div style={{ marginBottom: '12px' }}>
                <Row gutter={12}>
                  <Col span={24}>
                    <Text style={{ fontSize: '12px' }}>抓包进度: </Text>
                                         <Progress 
                       percent={Math.round(captureProgress)} 
                       status="active" 
                       size="small"
                       strokeColor={{
                         '0%': '#108ee9',
                         '50%': '#52c41a',
                         '100%': '#faad14',
                       }}
                       format={(percent) => `${percent}% (剩余 ${captureTimeLeft} 秒)`}
                     />
                  </Col>
                </Row>
                <Row gutter={12} style={{ marginTop: '8px' }}>
                  <Col span={12}>
                    <Text style={{ fontSize: '12px' }}>已抓包数据: {(captureDataSize / 1024).toFixed(2)} KB</Text>
                  </Col>
                  <Col span={12}>
                    <Text style={{ fontSize: '12px' }}>预计总时长: {form.getFieldValue('duration') || 60} 秒</Text>
                  </Col>
                </Row>
              </div>
            )}
                       <div 
              style={{
                backgroundColor: '#1e1e1e',
                color: '#ffffff',
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                fontSize: '12px',
                padding: '12px',
                borderRadius: '6px',
                border: '1px solid #333',
                minHeight: '200px',
                maxHeight: '400px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all'
              }}
            >
              {output || '命令输出将在这里显示...'}
            </div>
         </Card>
       )}

             {activeTool === 'tcpdump' && (
         <Card 
           size="small" 
           className="hover-lift tool-card"
           bodyStyle={{ padding: '16px' }}
         >
           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
             <Title level={4} style={{ margin: 0 }}>抓包历史</Title>
             <Button icon={<ReloadOutlined />} onClick={fetchCaptureHistory} size="small">
               刷新
             </Button>
           </div>
           <Table
             columns={captureColumns}
             dataSource={captureHistory}
             rowKey="id"
             pagination={{ pageSize: 8, size: 'small' }}
             size="small"
           />
         </Card>
       )}
    </div>
  );
};

export default NetworkTools;
