import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, message, Alert, Switch, Row, Col } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ReloadOutlined, InfoCircleOutlined, PoweroffOutlined, SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { getFirewallRules, addFirewallRule, updateFirewallRule, deleteFirewallRule, getFirewallConfig } from '../api/firewall';

const { Option } = Select;

const FirewallRules = () => {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState([]);
  const [filteredRules, setFilteredRules] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [currentMode, setCurrentMode] = useState('blacklist');
  const [form] = Form.useForm();
  
  // 搜索和筛选状态
  const [searchText, setSearchText] = useState('');
  const [actionFilter, setActionFilter] = useState('all');

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await getFirewallRules();
      setRules(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      message.error('获取防火墙规则失败');
      console.error('Fetch rules error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
    fetchFirewallConfig();
  }, []);

  // 搜索和筛选逻辑
  useEffect(() => {
    let filtered = rules;
    
    // 按动作筛选
    if (actionFilter !== 'all') {
      filtered = filtered.filter(rule => rule.action === actionFilter);
    }
    
    // 按搜索文本筛选
    if (searchText) {
      filtered = filtered.filter(rule => 
        rule.rule_name?.toLowerCase().includes(searchText.toLowerCase()) ||
        rule.description?.toLowerCase().includes(searchText.toLowerCase())
      );
    }
    
    setFilteredRules(filtered);
  }, [rules, searchText, actionFilter]);

  const fetchFirewallConfig = async () => {
    try {
      const response = await getFirewallConfig();
      setCurrentMode(response.data.mode);
    } catch (error) {
      console.error('获取防火墙配置失败:', error);
    }
  };





  const getModeTips = (mode) => {
    if (mode === 'whitelist') {
      return {
        title: '白名单模式规则提示',
        description: '在白名单模式下，只有明确允许的连接才能通过，其他所有连接都会被拒绝。',
        sourceExamples: [
          '单个IP: 192.168.1.100',
          'IP段: 192.168.1.0/24',
          '任意IP: 0.0.0.0/0'
        ],
        actionTip: '建议选择"允许"，因为白名单模式下需要明确允许连接'
      };
    } else {
      return {
        title: '黑名单模式规则提示',
        description: '在黑名单模式下，默认允许所有连接，只有明确拒绝的连接才会被阻止。',
        sourceExamples: [
          '恶意IP: 192.168.1.100',
          '恶意IP段: 192.168.1.0/24',
          '任意IP: 0.0.0.0/0'
        ],
        actionTip: '建议选择"拒绝"，因为黑名单模式下需要明确拒绝连接'
      };
    }
  };

  const handleAddRule = async (values) => {
    try {
      const ruleData = {
        ...values,
        protocol: 'tcp',
        destination: '0.0.0.0/0',
        port: '',
        action: values.action, // 使用表单中选择的动作
        rule_type: 'input',
        source_type: values.source_type || 'manual',
        is_active: true
      };
      
      await addFirewallRule(ruleData);
      // 显示30秒生效提示
      Modal.success({
        title: '规则添加成功',
        content: (
          <div>
            <p>✅ 规则已成功添加到防火墙</p>
            <p>⏰ <strong>重要提示：</strong>规则变更将在30秒后完全生效，请耐心等待</p>
            <p>💡 这是因为防火墙需要时间处理连接跟踪（conntrack）状态</p>
          </div>
        ),
        okText: '知道了',
        width: 500
      });
      setModalVisible(false);
      setEditingRule(null);
      form.resetFields();
      fetchRules();
    } catch (error) {
      message.error('添加规则失败');
      console.error('Add rule error:', error);
    }
  };

  const handleEditRule = async (values) => {
    try {
      await updateFirewallRule(editingRule.id, values);
      message.success('更新规则成功');
      setModalVisible(false);
      setEditingRule(null);
      form.resetFields();
      fetchRules();
    } catch (error) {
      message.error('更新规则失败');
      console.error('Update rule error:', error);
    }
  };

  const handleEdit = (record) => {
    setEditingRule(record);
    form.setFieldsValue({
      action: record.action, // 确保设置动作字段
      rule_name: record.rule_name,
      protocol: record.protocol,
      source: record.source,
      destination: record.destination,
      port: record.port,
      rule_type: record.rule_type,
      description: record.description,
      apply_immediately: true
    });
    setModalVisible(true);
  };

  const handleDeleteRule = async (ruleId) => {
    try {
      await deleteFirewallRule(ruleId);
      // 显示30秒生效提示
      Modal.success({
        title: '规则删除成功',
        content: (
          <div>
            <p>✅ 规则已成功从防火墙删除</p>
            <p>⏰ <strong>重要提示：</strong>规则变更将在30秒后完全生效，请耐心等待</p>
            <p>💡 这是因为防火墙需要时间处理连接跟踪（conntrack）状态</p>
          </div>
        ),
        okText: '知道了',
        width: 500
      });
      fetchRules();
    } catch (error) {
      message.error('删除规则失败');
      console.error('Delete rule error:', error);
    }
  };

  const columns = [
    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>规则名称</span>,
      dataIndex: 'rule_name',
      key: 'rule_name',
      width: 150,
      render: (name, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: '500', color: '#262626' }}>{name}</span>
          {record.source_type === 'self_service' && (
            <Tag color="blue" size="small" style={{ borderRadius: '4px' }}>自助</Tag>
          )}
        </div>
      )
    },
    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>IP地址/IP段</span>,
      dataIndex: 'source',
      key: 'source',
      width: 150,
      render: (source) => (
        <span style={{ 
          fontFamily: 'monospace', 
          fontSize: '13px',
          color: '#1890ff',
          fontWeight: '500'
        }}>
          {source}
        </span>
      ),
    },
    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>动作</span>,
      dataIndex: 'action',
      key: 'action',
      width: 100,
      render: (action) => (
        <Tag 
          color={action === 'accept' ? 'green' : 'red'}
          style={{ 
            borderRadius: '6px',
            fontWeight: '600',
            padding: '2px 8px'
          }}
        >
          {action === 'accept' ? '允许' : '拒绝'}
        </Tag>
      )
    },
    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>来源</span>,
      dataIndex: 'source_type',
      key: 'source_type',
      width: 100,
      render: (sourceType) => (
        <Tag 
          color={sourceType === 'self_service' ? 'blue' : 'default'}
          style={{ 
            borderRadius: '4px',
            fontWeight: '500'
          }}
        >
          {sourceType === 'self_service' ? '自助提交' : '手动添加'}
        </Tag>
      )
    },

    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>备注</span>,
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 150,
      render: (description) => (
        <span style={{ 
          color: description ? '#595959' : '#bfbfbf',
          fontStyle: description ? 'normal' : 'italic'
        }}>
          {description || '无备注'}
        </span>
      ),
    },
    {
      title: <span style={{ fontWeight: '600', color: '#262626' }}>操作</span>,
      key: 'action',
      width: 140,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            style={{
              borderRadius: '4px',
              color: '#1890ff',
              fontWeight: '500'
            }}
          >
            编辑
          </Button>
          <Button
            type="text"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteRule(record.id)}
            style={{
              borderRadius: '4px',
              fontWeight: '500'
            }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

    return (
    <div style={{ padding: '24px' }}>
      <div style={{ 
        marginBottom: '20px', 
        padding: '20px',
        background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)',
        borderRadius: '8px',
        border: '1px solid rgba(24, 144, 255, 0.1)'
      }}>
        {/* 第一行：操作按钮和规则统计 */}
        <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
          <Col flex="auto">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={() => {
                  setEditingRule(null);
                  form.resetFields();
                  setModalVisible(true);
                }}
                size="large"
                style={{
                  borderRadius: '6px',
                  fontWeight: '600',
                  boxShadow: '0 2px 4px rgba(24, 144, 255, 0.2)'
                }}
              >
                添加规则
              </Button>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={fetchRules}
                loading={loading}
                size="large"
                style={{
                  borderRadius: '6px',
                  fontWeight: '500'
                }}
              >
                刷新规则
              </Button>
            </div>
          </Col>
          <Col>
            <div style={{ 
              fontSize: '13px', 
              color: '#666',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <InfoCircleOutlined />
              <span>当前共有 {rules.length} 条规则</span>
            </div>
          </Col>
        </Row>
        
        {/* 第二行：搜索和筛选 */}
        <Row gutter={[16, 16]}>
          <Col span={8}>
            <Input
              placeholder="搜索规则名称或备注..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
              style={{ borderRadius: '6px' }}
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="筛选规则动作"
              value={actionFilter}
              onChange={setActionFilter}
              style={{ width: '100%', borderRadius: '6px' }}
              prefix={<FilterOutlined />}
            >
              <Option value="all">全部规则</Option>
              <Option value="accept">允许规则</Option>
              <Option value="drop">拒绝规则</Option>
            </Select>
          </Col>
          <Col span={10}>
            <div style={{ 
              fontSize: '12px', 
              color: '#666',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <FilterOutlined />
              <span>
                显示 {filteredRules.length} 条规则
                {searchText && ` (搜索: "${searchText}")`}
                {actionFilter !== 'all' && ` (${actionFilter === 'accept' ? '允许' : '拒绝'})`}
              </span>
            </div>
          </Col>
        </Row>
      </div>

      {/* 页面标题和说明 */}
      <div style={{ 
        marginBottom: '24px',
        padding: '20px 24px',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        borderRadius: '12px',
        border: '1px solid rgba(0, 0, 0, 0.06)'
      }}>
        <h1 style={{ 
          margin: '0 0 12px 0', 
          fontSize: '24px', 
          fontWeight: '700', 
          color: '#1a1a1a',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <SafetyOutlined style={{ color: '#1890ff' }} />
          防火墙规则管理
        </h1>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '16px',
          color: '#595959',
          fontSize: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: '500' }}>当前模式:</span>
            <Tag 
              color={currentMode === 'whitelist' ? 'orange' : 'blue'}
              style={{ 
                fontWeight: '600',
                borderRadius: '6px',
                padding: '2px 8px'
              }}
            >
              {currentMode === 'whitelist' ? '白名单模式' : '黑名单模式'}
            </Tag>
          </div>
          <div style={{ 
            width: '1px', 
            height: '16px', 
            background: 'rgba(0, 0, 0, 0.1)' 
          }} />
          <span>
            {currentMode === 'whitelist' 
              ? '只允许明确允许的连接，其他所有连接都会被拒绝' 
              : '默认允许所有连接，只拒绝明确拒绝的连接'
            }
          </span>
        </div>
      </div>

      <Card
        title={
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            fontSize: '16px',
            fontWeight: '600'
          }}>
            <FileTextOutlined style={{ color: '#1890ff' }} />
            规则列表
          </div>
        }
        style={{ 
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)'
        }}
        bodyStyle={{ padding: '16px' }}
      >
                 <Table
           columns={columns}
           dataSource={filteredRules}
           rowKey="id"
           loading={loading}
          pagination={{ 
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条规则`,
            size: 'default'
          }}
          rowClassName={(record, index) => 
            index % 2 === 0 ? 'table-row-light' : 'table-row-dark'
          }
          style={{
            borderRadius: '8px',
            overflow: 'hidden'
          }}
          className="custom-table"
        />
      </Card>

             <Modal
         title={editingRule ? "编辑防火墙规则" : "添加防火墙规则"}
         open={modalVisible}
         onCancel={() => {
           setModalVisible(false);
           setEditingRule(null);
           form.resetFields();
         }}
         footer={null}
         width={800}
       >
                 {/* 模式提示信息 */}
         {!editingRule && (
           <Alert
             message={getModeTips(currentMode).title}
             description={
               <div>
                 <p>{getModeTips(currentMode).description}</p>
                 <div style={{ marginTop: 8 }}>
                   <strong>IP地址样例：</strong>
                   <ul style={{ margin: '4px 0', paddingLeft: 20 }}>
                     {getModeTips(currentMode).sourceExamples.map((example, index) => (
                       <li key={index}>{example}</li>
                     ))}
                   </ul>
                   <p style={{ marginTop: 8, color: '#1890ff' }}>
                     <InfoCircleOutlined /> {getModeTips(currentMode).actionTip}
                   </p>
                 </div>
               </div>
             }
             type="info"
             showIcon
             style={{ marginBottom: 16 }}
           />
         )}

                   <Form
            form={form}
            layout="vertical"
            onFinish={editingRule ? handleEditRule : handleAddRule}
          >
            {/* 规则动作选择 */}
            <Form.Item
              name="action"
              label="规则动作"
              rules={[{ required: true, message: '请选择规则动作' }]}
              initialValue={currentMode === 'whitelist' ? 'accept' : 'drop'}
            >
              <Select
                placeholder="选择规则动作"
                style={{ borderRadius: '6px' }}
              >
                <Option value="accept">允许 (Accept)</Option>
                <Option value="drop">拒绝 (Drop)</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name="rule_name"
              label="规则名称"
              rules={[{ required: true, message: '请输入规则名称' }]}
            >
              <Input 
                placeholder={
                  currentMode === 'whitelist' 
                    ? "例如: 允许内网访问" 
                    : "例如: 拒绝恶意IP"
                } 
              />
            </Form.Item>

          <Form.Item
            name="source"
            label="IP地址/IP段"
            rules={[{ required: true, message: '请输入IP地址或IP段' }]}
          >
            <Input 
              placeholder="例如: 192.168.1.100 或 192.168.1.0/24" 
            />
          </Form.Item>

          <Form.Item
            name="description"
            label="备注"
          >
            <Input.TextArea 
              placeholder="可选，用于说明规则的用途" 
              rows={2} 
            />
          </Form.Item>

          <Form.Item
            name="apply_immediately"
            valuePropName="checked"
            initialValue={true}
            label="立即生效"
          >
            <Switch 
              checkedChildren="是" 
              unCheckedChildren="否"
              defaultChecked={true}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingRule ? '更新' : '添加'}
              </Button>
              <Button onClick={() => {
                setModalVisible(false);
                setEditingRule(null);
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

export default FirewallRules;
