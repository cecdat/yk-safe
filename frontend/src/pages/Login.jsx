import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [backgroundImage, setBackgroundImage] = useState('');
  const navigate = useNavigate();

  // 获取 Bing 每日壁纸
  useEffect(() => {
    const fetchBingWallpaper = async () => {
      try {
        const response = await fetch('https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US');
        const data = await response.json();
        if (data.images && data.images.length > 0) {
          const imageUrl = `https://www.bing.com${data.images[0].url}`;
          setBackgroundImage(imageUrl);
        }
      } catch (error) {
        console.warn('无法获取 Bing 壁纸，使用默认背景');
        // 如果获取失败，使用默认渐变背景
        setBackgroundImage('');
      }
    };

    fetchBingWallpaper();
  }, []);

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

  // 输入框样式
  const inputStyle = {
    height: '48px',
    borderRadius: '12px',
    border: '2px solid rgba(255, 255, 255, 0.3)',
    fontSize: '16px',
    background: 'rgba(255, 255, 255, 0.1)',
    color: '#ffffff',
    backdropFilter: 'blur(10px)',
    transition: 'all 0.3s ease'
  };

  return (
    <>
      <style>
        {`
          .login-input::placeholder {
            color: rgba(255, 255, 255, 0.7) !important;
          }
          .login-input:focus::placeholder {
            color: rgba(255, 255, 255, 0.9) !important;
          }
          .ant-input-password-icon {
            color: rgba(255, 255, 255, 0.7) !important;
          }
          .ant-input-password-icon:hover {
            color: rgba(255, 255, 255, 0.9) !important;
          }
        `}
      </style>
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: backgroundImage 
          ? `linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), url(${backgroundImage})`
          : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        position: 'relative'
      }}>
        <Card 
          title={
            <div style={{ 
              textAlign: 'center', 
              fontSize: '28px', 
              fontWeight: '600',
              color: '#ffffff',
              marginBottom: '8px',
              textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)'
            }}>
              YK-Safe 防火墙管理系统
            </div>
          }
          style={{ 
            width: 420, 
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            borderRadius: '16px',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(20px)',
            background: 'rgba(255, 255, 255, 0.1)'
          }}
          headStyle={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
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
                prefix={<UserOutlined style={{ color: '#ffffff' }} />} 
                placeholder="用户名" 
                className="login-input"
                style={inputStyle}
                onFocus={(e) => {
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.6)';
                  e.target.style.background = 'rgba(255, 255, 255, 0.2)';
                }}
                onBlur={(e) => {
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.3)';
                  e.target.style.background = 'rgba(255, 255, 255, 0.1)';
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码!' }]}
            >
              <Input.Password 
                prefix={<LockOutlined style={{ color: '#ffffff' }} />} 
                placeholder="密码" 
                className="login-input"
                style={inputStyle}
                onFocus={(e) => {
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.6)';
                  e.target.style.background = 'rgba(255, 255, 255, 0.2)';
                }}
                onBlur={(e) => {
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.3)';
                  e.target.style.background = 'rgba(255, 255, 255, 0.1)';
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: '0' }}>
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
                  background: 'rgba(255, 255, 255, 0.2)',
                  border: '2px solid rgba(255, 255, 255, 0.3)',
                  color: '#ffffff',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
                  transition: 'all 0.3s ease'
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.3)';
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.5)';
                  e.target.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = 'rgba(255, 255, 255, 0.2)';
                  e.target.style.border = '2px solid rgba(255, 255, 255, 0.3)';
                  e.target.style.transform = 'translateY(0)';
                }}
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </>
  );
};

export default Login;
