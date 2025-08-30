import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Space, Button, message, Progress, Tooltip, Badge } from 'antd';
import {
  SafetyOutlined,
  StopOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  DesktopOutlined,
  HddOutlined,
  DatabaseOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { 
  getDashboardData,
  getFirewallStatus, 
  getFirewallConfig,
  getSystemInfo, 
  getProcessInfo, 
  getContainerInfo 
} from '../api/monitor';
import { ensureObject } from '../utils/dataUtils';
import './Dashboard.css';

// 格式化字节大小
const formatBytes = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

const Dashboard = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    firewallStatus: { is_running: false, rules_count: 0 },
    firewallConfig: { mode: 'blacklist', description: '' },
    systemInfo: {
      cpu: { percent: 0, count: 0 },
      memory: { total: 0, used: 0, percent: 0 },
      disk: { total: 0, used: 0, percent: 0 },
      load: { load_1min: 0, load_5min: 0, load_15min: 0, load_per_cpu: 0 },
      disk_partitions: []
    },
    networkInfo: {
      connections: {
        total: 0,
        established: 0,
        listening: 0,
        time_wait: 0,
        close_wait: 0,
        top_ips: []
      },
      traffic: {
        bytes_sent: 0,
        bytes_recv: 0,
        packets_sent: 0,
        packets_recv: 0,
        errin: 0,
        errout: 0,
        dropin: 0,
        dropout: 0
      }
    },
    processInfo: {
      total_processes: 0,
      top_cpu_processes: [],
      top_memory_processes: []
    },
    containerInfo: {
      containers: [],
      total_containers: 0
    }
  });

  // 翻牌动画函数
  const flipToNumber = (element, newNumber) => {
    if (!element) return;
    
    const oldNumber = element.getAttribute('data-digit');
    if (oldNumber === newNumber.toString()) return;
    
    element.setAttribute('data-digit', newNumber);
    element.classList.add('flip-animation');
    
    // 动画中间更新数字
    setTimeout(() => {
      element.textContent = newNumber;
    }, 300);
    
    // 动画结束移除类
    setTimeout(() => {
      element.classList.remove('flip-animation');
    }, 600);
  };

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 优先使用综合仪表盘 API，性能更好
      const dashboardRes = await getDashboardData();
      
      if (dashboardRes.data && dashboardRes.data.code === 0) {
        const dashboardData = dashboardRes.data.data;
        
        // 同时获取防火墙配置信息
        const firewallConfigRes = await getFirewallConfig();
        
        setStats({
          firewallStatus: ensureObject(dashboardData.firewall_status, { is_running: false, rules_count: 0 }),
          firewallConfig: ensureObject(firewallConfigRes.data, { mode: 'blacklist', description: '' }),
          systemInfo: ensureObject(dashboardData.system_info, {
            cpu: { percent: 0, count: 0 },
            memory: { total: 0, used: 0, percent: 0 },
            disk: { total: 0, used: 0, percent: 0 },
            load: { load_1min: 0, load_5min: 0, load_15min: 0, load_per_cpu: 0 },
            disk_partitions: []
          }),
          networkInfo: ensureObject(dashboardData.network_info, {
            connections: {
              total: 0,
              established: 0,
              listening: 0,
              time_wait: 0,
              close_wait: 0,
              top_ips: []
            },
            traffic: {
              bytes_sent: 0,
              bytes_recv: 0,
              packets_sent: 0,
              packets_recv: 0,
              errin: 0,
              errout: 0,
              dropin: 0,
              dropout: 0
            }
          }),
          processInfo: ensureObject(dashboardData.process_info, {
            total_processes: 0,
            top_cpu_processes: [],
            top_memory_processes: []
          }),
          containerInfo: ensureObject(dashboardData.container_info, {
            containers: [],
            total_containers: 0
          })
        });
      } else {
        // 如果综合 API 失败，回退到原来的多个 API 调用
        console.warn('综合仪表盘 API 失败，回退到多个 API 调用');
        const [firewallRes, firewallConfigRes, systemRes, processRes, containerRes] = await Promise.all([
          getFirewallStatus(),
          getFirewallConfig(),
          getSystemInfo(),
          getProcessInfo(),
          getContainerInfo()
        ]);

        setStats({
          firewallStatus: ensureObject(firewallRes.data, { is_running: false, rules_count: 0 }),
          firewallConfig: ensureObject(firewallConfigRes.data, { mode: 'blacklist', description: '' }),
          systemInfo: ensureObject(systemRes.data, {
            cpu: { percent: 0, count: 0 },
            memory: { total: 0, used: 0, percent: 0 },
            disk: { total: 0, used: 0, percent: 0 },
            load: { load_1min: 0, load_5min: 0, load_15min: 0, load_per_cpu: 0 },
            disk_partitions: []
          }),
          processInfo: ensureObject(processRes.data, {
            total_processes: 0,
            top_cpu_processes: [],
            top_memory_processes: []
          }),
          containerInfo: ensureObject(containerRes.data, {
            containers: [],
            total_containers: 0
          })
        });
      }
    } catch (error) {
      message.error('获取仪表盘数据失败');
      console.error('Dashboard data fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // 每30秒刷新一次数据
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const processColumns = [
    {
      title: 'PID',
      dataIndex: 'pid',
      key: 'pid',
      width: 80,
    },
    {
      title: '进程名',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: 'CPU使用率',
      dataIndex: 'cpu_percent',
      key: 'cpu_percent',
      width: 120,
      render: (value) => (
        <span style={{ color: value > 80 ? '#ff4d4f' : '#52c41a' }}>
          {parseFloat(value).toFixed(2)}%
        </span>
      ),
    },
    {
      title: '内存使用率',
      dataIndex: 'memory_percent',
      key: 'memory_percent',
      width: 120,
      render: (value) => (
        <span style={{ color: value > 80 ? '#ff4d4f' : '#52c41a' }}>
          {parseFloat(value).toFixed(2)}%
        </span>
      ),
    },
  ];

  const containerColumns = [
    {
      title: '容器名',
      dataIndex: 'name',
      key: 'name',
      width: 120,
      ellipsis: true,
    },
    {
      title: '容器ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (id) => (
        <Tooltip title={id} placement="top">
          <span style={{ fontFamily: 'monospace', fontSize: '11px' }}>
            {id.substring(0, 8)}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '镜像',
      dataIndex: 'image',
      key: 'image',
      width: 180,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status) => {
        let color = 'default';
        let text = status;
        
        if (status.includes('Up') || status === 'running') {
          color = 'green';
          text = '运行中';
        } else if (status.includes('Exited') || status === 'exited') {
          color = 'red';
          text = '已停止';
        } else if (status.includes('Created') || status === 'created') {
          color = 'orange';
          text = '已创建';
        } else if (status.includes('Restarting') || status === 'restarting') {
          color = 'yellow';
          text = '重启中';
        } else if (status.includes('Paused') || status === 'paused') {
          color = 'default';
          text = '已暂停';
        }
        
        return <Tag color={color}>{text}</Tag>;
      },
    },
    {
      title: '端口映射',
      dataIndex: 'ports',
      key: 'ports',
      width: 200,
      render: (ports, record) => {
        if (!ports || ports === '无端口映射' || ports === '获取失败') {
          return <span style={{ color: '#999' }}>{ports || '无端口映射'}</span>;
        }
        
        // 处理字符串格式的端口映射
        if (typeof ports === 'string') {
          const portMappings = ports.split(', ').filter(p => p.trim());
          if (portMappings.length === 0) return <span style={{ color: '#999' }}>无端口映射</span>;
          
          return (
            <div>
              {portMappings.map((port, index) => (
                <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                  {port}
                </Tag>
              ))}
            </div>
          );
        }
        
        // 处理对象格式的端口映射（来自Docker API）
        if (typeof ports === 'object' && ports !== null) {
          const portMappings = [];
          for (const [containerPort, hostBindings] of Object.entries(ports)) {
            if (hostBindings && Array.isArray(hostBindings)) {
              for (const binding of hostBindings) {
                const hostIp = binding.HostIp || '0.0.0.0';
                const hostPort = binding.HostPort || '';
                portMappings.push(`${hostIp}:${hostPort}->${containerPort}`);
              }
            }
          }
          
          if (portMappings.length === 0) return <span style={{ color: '#999' }}>无端口映射</span>;
          
          return (
            <div>
              {portMappings.map((port, index) => (
                <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
                  {port}
                </Tag>
              ))}
            </div>
          );
        }
        
        return <span style={{ color: '#999' }}>无端口映射</span>;
      },
    },
    {
      title: '路径映射',
      dataIndex: 'mounts',
      key: 'mounts',
      width: 200,
      render: (mounts, record) => {
        if (!mounts || mounts.length === 0) return <span style={{ color: '#999' }}>无路径映射</span>;
        
        // 处理字符串数组格式的挂载信息
        if (Array.isArray(mounts)) {
          // 过滤掉时区映射和系统映射
          const filteredMounts = mounts.filter(mount => 
            !mount.includes('/usr/share/zoneinfo') && 
            !mount.includes('/etc/localtime') &&
            !mount.includes('/etc/timezone') &&
            !mount.includes('/proc/') &&
            !mount.includes('/sys/') &&
            !mount.includes('/dev/')
          );
          
          if (filteredMounts.length === 0) return <span style={{ color: '#999' }}>无路径映射</span>;
          
          return (
            <div>
              {filteredMounts.slice(0, 3).map((mount, index) => {
                // 确保 mount 是字符串类型
                const mountString = typeof mount === 'string' ? mount : String(mount);
                const mountParts = mountString.split(':');
                
                return (
                  <Tooltip 
                    key={index} 
                    title={mountString}
                    placement="top"
                  >
                    <Tag color="green" style={{ marginBottom: 4 }}>
                      {mountParts[0]?.split('/').pop() || 'unknown'} → {mountParts[1]?.split('/').pop() || 'unknown'}
                    </Tag>
                  </Tooltip>
                );
              })}
              {filteredMounts.length > 3 && (
                <Tag color="default">+{filteredMounts.length - 3}</Tag>
              )}
            </div>
          );
        }
        
        return <span style={{ color: '#999' }}>无路径映射</span>;
      },
    },
    {
      title: 'CPU使用率',
      dataIndex: 'cpu_percent',
      key: 'cpu_percent',
      width: 100,
      render: (value) => {
        if (!value || value === 'N/A' || value === '0.00') {
          return <span style={{ color: '#999' }}>N/A</span>;
        }
        const numValue = parseFloat(value);
        return (
          <span style={{ color: numValue > 80 ? '#ff4d4f' : '#52c41a' }}>
            {numValue.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '内存使用率',
      dataIndex: 'memory_percent',
      key: 'memory_percent',
      width: 100,
      render: (value) => {
        if (!value || value === 'N/A' || value === '0') {
          return <span style={{ color: '#999' }}>N/A</span>;
        }
        const numValue = parseFloat(value);
        return (
          <span style={{ color: numValue > 80 ? '#ff4d4f' : '#52c41a' }}>
            {numValue.toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created',
      key: 'created',
      width: 120,
      render: (created) => {
        if (!created || created === 'N/A') return <span style={{ color: '#999' }}>N/A</span>;
        try {
          // 处理ISO格式时间字符串
          if (typeof created === 'string' && created.includes('T')) {
            const date = new Date(created);
            return <span style={{ fontSize: '11px' }}>{date.toLocaleDateString()}</span>;
          }
          // 处理其他格式
          return <span style={{ fontSize: '11px' }}>{created}</span>;
        } catch {
          return <span style={{ color: '#999' }}>格式错误</span>;
        }
      },
    },
  ];

  return (
    <div className="glass-cards-container">
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h2 className="page-title">系统概览</h2>
        </div>
        <Button 
          type="primary" 
          icon={<ReloadOutlined />} 
          onClick={fetchDashboardData}
          loading={loading}
        >
          刷新数据
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        {/* 第一行：防火墙状态、CPU使用率、内存使用率、系统负载、网络连接数 */}
        <Col span={4.8}>
          <Card 
            className="glass-card firewall-card"
            size="small" 
            style={{ height: '140px' }}
          >
            <div className="card-title firewall-title">
              <SafetyOutlined className="mr-2" />
              防火墙状态
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div className="status-value">
                    <div className="flip-container">
                      <div className="flip-digit" data-digit={stats.firewallStatus.is_running ? '1' : '0'}>
                        {stats.firewallStatus.is_running ? '1' : '0'}
                      </div>
                    </div>
                    <span className="status-text">{stats.firewallStatus.is_running ? '运行中' : '已停止'}</span>
                  </div>
                  <div style={{ marginTop: 8, fontSize: '12px' }}>
                    <Tag color={stats.firewallStatus.is_running ? 'green' : 'red'}>
                      {stats.firewallStatus.is_running ? '运行' : '停止'}
                    </Tag>
                    <Tag color="blue" style={{ marginLeft: 8 }}>
                      规则: {stats.firewallStatus.rules_count || 0}
                    </Tag>
                  </div>
                </div>
                <SafetyOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
              </div>
            </div>
          </Card>
        </Col>
        <Col span={4.8}>
          <Card 
            className="glass-card cpu-card"
            style={{ height: '140px' }}
          >
            <div className="card-title cpu-title">
              <DesktopOutlined className="mr-2" />
              CPU使用率
            </div>
            <div className="card-content">
              <div className="cpu-value">
                <div className="flip-container">
                  <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.cpu.percent / 10)}>
                    {Math.floor(stats.systemInfo.cpu.percent / 10)}
                  </div>
                </div>
                <div className="flip-container">
                  <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.cpu.percent % 10)}>
                    {Math.floor(stats.systemInfo.cpu.percent % 10)}
                  </div>
                </div>
                <span className="unit">%</span>
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: '#6B7A6B' }}>
                核心数: {stats.systemInfo.cpu.count || 'N/A'}
              </div>
            </div>
          </Card>
        </Col>
        <Col span={4.8}>
          <Card 
            className="glass-card memory-card"
            style={{ height: '140px' }}
          >
            <div className="card-title memory-title">
              <HddOutlined className="mr-2" />
              内存使用率
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div className="memory-value">
                    <div className="flip-container">
                      <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.memory.percent / 10)}>
                        {Math.floor(stats.systemInfo.memory.percent / 10)}
                      </div>
                    </div>
                    <div className="flip-container">
                      <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.memory.percent % 10)}>
                        {Math.floor(stats.systemInfo.memory.percent % 10)}
                      </div>
                    </div>
                    <span className="unit">%</span>
                  </div>
                  <div style={{ marginTop: 8, fontSize: '12px' }}>
                    <div>总内存: {formatBytes(stats.systemInfo.memory.total)}</div>
                    <div>已使用: {formatBytes(stats.systemInfo.memory.used)}</div>
                    <div>可用: {formatBytes(stats.systemInfo.memory.free)}</div>
                  </div>
                </div>
                <div style={{ width: 80, height: 80 }}>
                  <Progress
                    type="circle"
                    percent={stats.systemInfo.memory.percent}
                    size={80}
                    strokeColor={
                      stats.systemInfo.memory.percent > 90 ? '#ff4d4f' : 
                      stats.systemInfo.memory.percent > 80 ? '#faad14' : '#52c41a'
                    }
                    format={(percent) => `${Math.round(percent)}%`}
                  />
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={4.8}>
          <Card 
            className="glass-card load-card"
            style={{ height: '140px' }}
          >
            <div className="card-title load-title">
              <DesktopOutlined className="mr-2" />
              系统负载
            </div>
            <div className="card-content">
              <div className="load-value">
                <div className="flip-container">
                  <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.load.load_1min)}>
                    {Math.floor(stats.systemInfo.load.load_1min)}
                  </div>
                </div>
                <span className="decimal">.{Math.floor((stats.systemInfo.load.load_1min % 1) * 10)}</span>
              </div>
              <div style={{ marginTop: 8, fontSize: '12px' }}>
                <div>1分钟: {stats.systemInfo.load.load_1min}</div>
                <div>5分钟: {stats.systemInfo.load.load_5min}</div>
                <div>15分钟: {stats.systemInfo.load.load_15min}</div>
                <div>每CPU: {stats.systemInfo.load.load_per_cpu}</div>
              </div>
            </div>
          </Card>
        </Col>
        <Col span={4.8}>
          <Card 
            className="glass-card network-card"
            style={{ height: '140px' }}
          >
            <div className="card-title network-title">
              <DesktopOutlined className="mr-2" />
              网络连接数
            </div>
            <div className="card-content">
              <div className="network-value">
                <div className="flip-container">
                  <div className="flip-digit" data-digit={Math.floor(stats.networkInfo.connections.total / 1000)}>
                    {Math.floor(stats.networkInfo.connections.total / 1000)}
                  </div>
                </div>
                <span className="unit">K</span>
              </div>
              <div style={{ marginTop: 8, fontSize: '12px' }}>
                {stats.networkInfo.connections.top_ips && stats.networkInfo.connections.top_ips.length > 0 && (
                  <div>
                    <div style={{ fontWeight: 'bold', marginBottom: 4 }}>TOP5 IP:</div>
                    {stats.networkInfo.connections.top_ips.slice(0, 5).map((item, index) => (
                      <div key={index} style={{ fontSize: '11px', marginBottom: 2 }}>
                        {item.ip} ({item.count})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 第二行：磁盘使用情况、网络流量统计 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card className="glass-card disk-card">
            <div className="card-title disk-title">
              <HddOutlined className="mr-2" />
              磁盘使用情况
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <div className="disk-value">
                  <div className="flip-container">
                    <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.disk.percent / 10)}>
                      {Math.floor(stats.systemInfo.disk.percent / 10)}
                    </div>
                  </div>
                  <div className="flip-container">
                    <div className="flip-digit" data-digit={Math.floor(stats.systemInfo.disk.percent % 10)}>
                      {Math.floor(stats.systemInfo.disk.percent % 10)}
                    </div>
                  </div>
                  <span className="unit">%</span>
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', justifyContent: 'center' }}>
                {/* 主磁盘 */}
                <div style={{ textAlign: 'center' }}>
                  <Progress
                    type="circle"
                    percent={stats.systemInfo.disk.percent}
                    size={80}
                    strokeColor={stats.systemInfo.disk.percent > 90 ? '#ff4d4f' : '#52c41a'}
                    format={(percent) => (
                      <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
                        <div>根目录</div>
                        <div>{Math.round(percent)}%</div>
                      </div>
                    )}
                  />
                  <div style={{ marginTop: 8, fontSize: '11px', color: '#666' }}>
                    {formatBytes(stats.systemInfo.disk.used)} / {formatBytes(stats.systemInfo.disk.total)}
                  </div>
                </div>
                
                {/* 其他磁盘分区 */}
                {stats.systemInfo.disk_partitions && stats.systemInfo.disk_partitions.length > 0 && 
                  stats.systemInfo.disk_partitions.slice(0, 3).map((partition, index) => (
                    <div key={index} style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        percent={partition.percent}
                        size={80}
                        strokeColor={partition.percent > 90 ? '#ff4d4f' : '#52c41a'}
                        format={(percent) => (
                          <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
                            <div>{partition.mountpoint.split('/').pop() || '分区'}</div>
                            <div>{Math.round(percent)}%</div>
                          </div>
                        )}
                      />
                      <div style={{ marginTop: 8, fontSize: '11px', color: '#666' }}>
                        {formatBytes(partition.used)} / {formatBytes(partition.total)}
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card className="glass-card traffic-card">
            <div className="card-title traffic-title">
              <DesktopOutlined className="mr-2" />
              网络流量统计
            </div>
            <div className="card-content">
              <div className="traffic-value">
                {formatBytes(stats.networkInfo.traffic.bytes_sent + stats.networkInfo.traffic.bytes_recv)}
              </div>
              <div style={{ marginTop: 8, fontSize: '12px' }}>
                <div>发送: {formatBytes(stats.networkInfo.traffic.bytes_sent)}</div>
                <div>接收: {formatBytes(stats.networkInfo.traffic.bytes_recv)}</div>
                <div>发送包: {stats.networkInfo.traffic.packets_sent}</div>
                <div>接收包: {stats.networkInfo.traffic.packets_recv}</div>
                {(stats.networkInfo.traffic.errin > 0 || stats.networkInfo.traffic.errout > 0 || 
                  stats.networkInfo.traffic.dropin > 0 || stats.networkInfo.traffic.dropout > 0) && (
                  <div style={{ marginTop: 4 }}>
                    <Badge color="red" text={`错误: ${stats.networkInfo.traffic.errin + stats.networkInfo.traffic.errout}`} />
                    <Badge color="orange" text={`丢包: ${stats.networkInfo.traffic.dropin + stats.networkInfo.traffic.dropout}`} />
                  </div>
                )}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 进程监控卡片 */}
       <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
         <Col span={12}>
           <Card title="CPU占用最高的进程" size="small" className="glass-card">
             <Table
               columns={processColumns}
               dataSource={stats.processInfo.top_cpu_processes}
               rowKey="pid"
               pagination={false}
               size="small"
               loading={loading}
               scroll={{ y: 300 }}
             />
           </Card>
         </Col>
         <Col span={12}>
           <Card title="内存占用最高的进程" size="small" className="glass-card">
             <Table
               columns={processColumns}
               dataSource={stats.processInfo.top_memory_processes}
               rowKey="pid"
               pagination={false}
               size="small"
               loading={loading}
               scroll={{ y: 300 }}
             />
           </Card>
         </Col>
       </Row>

               {/* 容器监控卡片 */}
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col span={24}>
            <Card title={`Docker容器监控 (${stats.containerInfo.total_containers || 0}个运行中)`} size="small" className="glass-card">
              {stats.containerInfo.containers && stats.containerInfo.containers.length > 0 ? (
                <Table
                  columns={containerColumns}
                  dataSource={stats.containerInfo.containers}
                  rowKey="name"
                  pagination={false}
                  size="small"
                  loading={loading}
                  scroll={{ x: 800 }}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                  暂无运行中的Docker容器
                  {stats.containerInfo.debug_info && stats.containerInfo.debug_info.length > 0 && (
                    <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
                      <details>
                        <summary style={{ cursor: 'pointer', color: '#1890ff' }}>查看调试信息</summary>
                        <div style={{ marginTop: '10px', textAlign: 'left', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
                          {stats.containerInfo.debug_info.map((info, index) => (
                            <div key={index} style={{ marginBottom: '5px', fontFamily: 'monospace' }}>• {info}</div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              )}
            </Card>
          </Col>
        </Row>
    </div>
  );
};

export default Dashboard;
