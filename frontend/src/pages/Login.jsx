import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, message, Spin } from 'antd';
import { UserOutlined, LockOutlined, LoadingOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { getWallpaperInfo } from '../api/external';
import './Login.css';

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [wallpaperLoading, setWallpaperLoading] = useState(true);
  const [wallpaperInfo, setWallpaperInfo] = useState({
    url: null,
    title: 'YK-Safe 防火墙管理系统',
    copyright: 'YK-Safe',
    copyrightLink: '#'
  });
  const navigate = useNavigate();

  // 获取壁纸信息
  useEffect(() => {
    const fetchWallpaper = async () => {
      try {
        setWallpaperLoading(true);
        const info = await getWallpaperInfo();
        setWallpaperInfo(info);
      } catch (error) {
        console.warn('无法获取壁纸，使用默认背景');
        // 使用默认信息
        setWallpaperInfo({
          url: null,
          title: 'YK-Safe 防火墙管理系统',
          copyright: 'YK-Safe',
          copyrightLink: '#'
        });
      } finally {
        setWallpaperLoading(false);
      }
    };

    fetchWallpaper();
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

  // 背景样式
  const backgroundStyle = {
    background: wallpaperInfo.url 
      ? `linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), url(${wallpaperInfo.url})`
      : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat'
  };

  return (
    <div className="login-container" style={backgroundStyle}>
      {/* 壁纸加载动画 */}
      {wallpaperLoading && (
        <div className="wallpaper-loading-spinner">
          <Spin 
            indicator={<LoadingOutlined style={{ fontSize: 24, color: '#ffffff' }} spin />}
            tip="正在加载背景..."
          />
        </div>
      )}

      {/* 版权信息 */}
      {!wallpaperLoading && wallpaperInfo.copyright && (
        <div className="wallpaper-copyright">
          <a 
            href={wallpaperInfo.copyrightLink} 
            target="_blank" 
            rel="noopener noreferrer"
            style={{ color: 'inherit', textDecoration: 'none' }}
          >
            © {wallpaperInfo.copyright}
          </a>
        </div>
      )}

      <Card className="login-card">
        <div className="login-header">
          <h2 style={{ 
            color: '#ffffff', 
            textShadow: '0 2px 4px rgba(0, 0, 0, 0.3)',
            marginBottom: '8px'
          }}>
            {wallpaperInfo.title}
          </h2>
          <p style={{ 
            color: 'rgba(255, 255, 255, 0.8)',
            margin: 0
          }}>
            安全防护，智能管理
          </p>
        </div>

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
              prefix={<UserOutlined className="login-icon" />} 
              placeholder="用户名" 
              className="login-input"
              style={{
                height: '48px',
                borderRadius: '12px',
                fontSize: '16px'
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码!' }]}
          >
            <Input.Password 
              prefix={<LockOutlined className="login-icon" />} 
              placeholder="密码" 
              className="login-input"
              style={{
                height: '48px',
                borderRadius: '12px',
                fontSize: '16px'
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: '0' }}>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              className="login-button"
              style={{ 
                width: '100%',
                height: '48px',
                borderRadius: '12px',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default Login;
