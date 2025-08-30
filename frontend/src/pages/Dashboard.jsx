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
        if (status.includes('Up')) color = 'green';
        else if (status.includes('Exited')) color = 'red';
        else if (status.includes('Created')) color = 'orange';
        return <Tag color={color}>{status}</Tag>;
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
        
        // 解析端口映射字符串
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
      },
    },
    {
      title: '路径映射',
      dataIndex: 'mounts',
      key: 'mounts',
      width: 200,
      render: (mounts, record) => {
        if (!mounts || mounts.length === 0) return <span style={{ color: '#999' }}>无路径映射</span>;
        
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
            {filteredMounts.slice(0, 3).map((mount, index) => (
              <Tooltip 
                key={index} 
                title={mount}
                placement="top"
              >
                <Tag color="green" style={{ marginBottom: 4 }}>
                  {mount.split(':')[0]?.split('/').pop() || 'unknown'} → {mount.split(':')[1]?.split('/').pop() || 'unknown'}
                </Tag>
              </Tooltip>
            ))}
            {filteredMounts.length > 3 && (
              <Tag color="default">+{filteredMounts.length - 3}</Tag>
            )}
          </div>
        );
      },
    },
    {
      title: 'CPU使用率',
      dataIndex: 'cpu_percent',
      key: 'cpu_percent',
      width: 100,
      render: (value) => (
        <span style={{ color: parseFloat(value) > 80 ? '#ff4d4f' : '#52c41a' }}>
          {parseFloat(value).toFixed(2)}%
        </span>
      ),
    },
    {
      title: '内存使用率',
      dataIndex: 'memory_percent',
      key: 'memory_percent',
      width: 100,
      render: (value) => (
        <span style={{ color: parseFloat(value) > 80 ? '#ff4d4f' : '#52c41a' }}>
          {parseFloat(value).toFixed(2)}%
        </span>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created',
      key: 'created',
      width: 120,
      render: (created) => {
        if (!created || created === 'N/A') return <span style={{ color: '#999' }}>N/A</span>;
        try {
          const date = new Date(created);
          return <span style={{ fontSize: '11px' }}>{date.toLocaleDateString()}</span>;
        } catch {
          return <span style={{ color: '#999' }}>格式错误</span>;
        }
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
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
        <Col span={6}>
          <Card className="hover-lift">
            <Statistic
              title="防火墙状态"
              value={stats.firewallStatus.is_running ? '运行中' : '已停止'}
              valueStyle={{
                color: stats.firewallStatus.is_running ? '#52c41a' : '#ff4d4f'
              }}
              prefix={stats.firewallStatus.is_running ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="hover-lift">
            <Statistic
              title="防护规则"
              value={stats.firewallStatus.rules_count}
              valueStyle={{ color: '#1890ff' }}
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
                 <Col span={6}>
           <Card className="hover-lift">
             <Statistic
               title="CPU使用率"
               value={stats.systemInfo.cpu.percent}
               precision={2}
               suffix="%"
               valueStyle={{ color: stats.systemInfo.cpu.percent > 80 ? '#ff4d4f' : '#52c41a' }}
               prefix={<DesktopOutlined />}
             />
             <div style={{ marginTop: 8, fontSize: 12, color: '#6B7A6B' }}>
               核心数: {stats.systemInfo.cpu.count || 'N/A'}
             </div>
           </Card>
         </Col>
         <Col span={6}>
           <Card className="hover-lift">
             <Statistic
               title="内存使用率"
               value={stats.systemInfo.memory.percent}
               precision={2}
               suffix="%"
               valueStyle={{ color: stats.systemInfo.memory.percent > 80 ? '#ff4d4f' : '#52c41a' }}
               prefix={<DatabaseOutlined />}
             />
           </Card>
         </Col>
      </Row>

      {/* 系统负载和磁盘使用卡片 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card 
            title={
              <Space>
                系统负载
                {(() => {
                  const cpuCount = stats.systemInfo.cpu.count || 1;
                  const load1min = stats.systemInfo.load.load_1min;
                  if (load1min > cpuCount * 2.5) {
                    return <Badge color="red" text="严重超载" />;
                  } else if (load1min > cpuCount * 1.5) {
                    return <Badge color="orange" text="负载较高" />;
                  }
                  return null;
                })()}
              </Space>
            } 
            size="small"
            className="hover-lift system-load-card"
          >
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="1分钟"
                  value={stats.systemInfo.load.load_1min}
                  precision={2}
                  valueStyle={{ 
                    color: (() => {
                      const cpuCount = stats.systemInfo.cpu.count || 1;
                      const load = stats.systemInfo.load.load_1min;
                      if (load > cpuCount * 2.5) return '#ff4d4f';
                      if (load > cpuCount * 1.5) return '#faad14';
                      return '#52c41a';
                    })()
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="5分钟"
                  value={stats.systemInfo.load.load_5min}
                  precision={2}
                  valueStyle={{ 
                    color: (() => {
                      const cpuCount = stats.systemInfo.cpu.count || 1;
                      const load = stats.systemInfo.load.load_5min;
                      if (load > cpuCount * 2.5) return '#ff4d4f';
                      if (load > cpuCount * 1.5) return '#faad14';
                      return '#52c41a';
                    })()
                  }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="15分钟"
                  value={stats.systemInfo.load.load_15min}
                  precision={2}
                  valueStyle={{ 
                    color: (() => {
                      const cpuCount = stats.systemInfo.cpu.count || 1;
                      const load = stats.systemInfo.load.load_15min;
                      if (load > cpuCount * 2.5) return '#ff4d4f';
                      if (load > cpuCount * 1.5) return '#faad14';
                      return '#52c41a';
                    })()
                  }}
                />
              </Col>
            </Row>
            <div style={{ marginTop: 16 }}>
              <div style={{ marginBottom: 8 }}>
                <span>每CPU负载: {parseFloat(stats.systemInfo.load.load_per_cpu).toFixed(2)}</span>
              </div>
              <Progress 
                percent={Math.min((stats.systemInfo.load.load_1min / (stats.systemInfo.cpu.count || 1)) * 100, 100)} 
                size="small"
                status={(() => {
                  const cpuCount = stats.systemInfo.cpu.count || 1;
                  const load = stats.systemInfo.load.load_1min;
                  if (load > cpuCount * 2.5) return 'exception';
                  if (load > cpuCount * 1.5) return 'active';
                  return 'normal';
                })()}
              />
            </div>
          </Card>
        </Col>
        
        <Col span={12}>
          <Card 
            title={
              <Space>
                磁盘使用情况
                {(() => {
                  const diskPercent = stats.systemInfo.disk.percent;
                  if (diskPercent > 95) {
                    return <Badge color="red" text="磁盘空间不足" />;
                  } else if (diskPercent > 80) {
                    return <Badge color="orange" text="磁盘空间紧张" />;
                  }
                  return null;
                })()}
              </Space>
            } 
            size="small"
            className="hover-lift system-load-card"
          >
            <Row gutter={16}>
              <Col span={8}>
                <Statistic
                  title="总容量"
                  value={formatBytes(stats.systemInfo.disk.total)}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="已使用"
                  value={formatBytes(stats.systemInfo.disk.used)}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={8}>
                <Statistic
                  title="使用率"
                  value={stats.systemInfo.disk.percent}
                  precision={1}
                  suffix="%"
                  valueStyle={{ 
                    color: (() => {
                      const percent = stats.systemInfo.disk.percent;
                      if (percent > 95) return '#ff4d4f';
                      if (percent > 80) return '#faad14';
                      return '#52c41a';
                    })()
                  }}
                />
              </Col>
            </Row>
            <div style={{ marginTop: 16 }}>
              <Progress 
                percent={stats.systemInfo.disk.percent} 
                size="small"
                status={(() => {
                  const percent = stats.systemInfo.disk.percent;
                  if (percent > 95) return 'exception';
                  if (percent > 80) return 'active';
                  return 'normal';
                })()}
                format={() => null}
              />
            </div>
            
            {/* 多磁盘分区信息 */}
            {stats.systemInfo.disk_partitions && stats.systemInfo.disk_partitions.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>分区详情:</div>
                {stats.systemInfo.disk_partitions.slice(0, 3).map((partition, index) => (
                  <div key={index} style={{ fontSize: 11, marginBottom: 4 }}>
                    <span style={{ color: '#666' }}>{partition.mountpoint}:</span>
                    <span style={{ 
                      color: partition.percent > 95 ? '#ff4d4f' : 
                             partition.percent > 80 ? '#faad14' : '#52c41a' 
                    }}>
                      {parseFloat(partition.percent).toFixed(2)}%
                    </span>
                    <span style={{ color: '#999', marginLeft: 8 }}>
                      ({formatBytes(partition.used)} / {formatBytes(partition.total)})
                    </span>
                  </div>
                ))}
                {stats.systemInfo.disk_partitions.length > 3 && (
                  <div style={{ fontSize: 11, color: '#999' }}>
                    还有 {stats.systemInfo.disk_partitions.length - 3} 个分区...
                  </div>
                )}
              </div>
            )}
          </Card>
        </Col>
      </Row>



       {/* 进程监控卡片 */}
       <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
         <Col span={12}>
           <Card title="CPU占用最高的进程" size="small">
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
           <Card title="内存占用最高的进程" size="small">
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
            <Card title={`Docker容器监控 (${stats.containerInfo.total_containers || 0}个运行中)`} size="small" className="hover-lift">
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
                            <div key={index} style={{ marginBottom: '5px' }}>• {info}</div>
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
