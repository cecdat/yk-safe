import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/auth/login', values);
      if (response.data.code === 0) {
        localStorage.setItem('token', response.data.data.access_token);
        message.success('登录成功');
        navigate('/dashboard');
      } else {
        message.error(response.data.message || '登录失败');
      }
    } catch (error) {
      console.error('Login error:', error);
      message.error('登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #7FB069 0%, #A8D5BA 50%, #F5F9F2 100%)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* 装饰性背景元素 */}
      <div style={{
        position: 'absolute',
        top: '10%',
        left: '10%',
        width: '200px',
        height: '200px',
        background: 'rgba(127, 176, 105, 0.1)',
        borderRadius: '50%',
        filter: 'blur(40px)'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '10%',
        right: '10%',
        width: '300px',
        height: '300px',
        background: 'rgba(168, 213, 186, 0.1)',
        borderRadius: '50%',
        filter: 'blur(60px)'
      }} />
      
      <Card 
        title={
          <div style={{ 
            textAlign: 'center', 
            fontSize: '28px', 
            fontWeight: '600',
            color: '#4A5D4A',
            marginBottom: '8px'
          }}>
            YK-Safe 封神云防护系统
          </div>
        }
        style={{ 
          width: 420, 
          boxShadow: '0 8px 32px rgba(127, 176, 105, 0.2)',
          borderRadius: '16px',
          border: '1px solid rgba(127, 176, 105, 0.1)',
          backdropFilter: 'blur(10px)',
          background: 'rgba(255, 255, 255, 0.95)'
        }}
        headStyle={{
          background: 'linear-gradient(135deg, #7FB069 0%, #A8D5BA 100%)',
          borderBottom: 'none',
          borderRadius: '16px 16px 0 0',
          padding: '24px 24px 16px 24px'
        }}
        bodyStyle={{
          padding: '32px 24px 24px 24px'
        }}
      >
        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名!' }]}
          >
            <Input 
              prefix={<UserOutlined style={{ color: '#7FB069' }} />} 
              placeholder="用户名" 
              style={{
                height: '48px',
                borderRadius: '12px',
                border: '2px solid #E8F0E8',
                fontSize: '16px'
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码!' }]}
          >
            <Input.Password 
              prefix={<LockOutlined style={{ color: '#7FB069' }} />} 
              placeholder="密码" 
              style={{
                height: '48px',
                borderRadius: '12px',
                border: '2px solid #E8F0E8',
                fontSize: '16px'
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: '16px' }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              style={{ 
                width: '100%',
                height: '48px',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: '600',
                background: 'linear-gradient(135deg, #7FB069 0%, #A8D5BA 100%)',
                border: 'none',
                boxShadow: '0 4px 16px rgba(127, 176, 105, 0.3)'
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
        
        <div style={{ 
          textAlign: 'center', 
          color: '#6B7A6B', 
          fontSize: '14px',
          padding: '16px',
          background: 'rgba(127, 176, 105, 0.05)',
          borderRadius: '8px',
          border: '1px solid rgba(127, 176, 105, 0.1)'
        }}>
          <div style={{ fontWeight: '500', marginBottom: '4px' }}>默认账户</div>
          <div>用户名: admin</div>
          <div>密码: admin123</div>
        </div>
      </Card>
    </div>
  );
};

export default Login;
