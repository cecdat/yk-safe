import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Spin, message, Badge } from 'antd';
import { UserOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';
import { getWallpaperInfo } from '../api/external';
import './Login.css';

const Login = () => {
  const [loading, setLoading] = useState(true);
  const [wallpaperUrl, setWallpaperUrl] = useState('');
  const [wallpaperLoaded, setWallpaperLoaded] = useState(false);
  const [wallpaperInfo, setWallpaperInfo] = useState({ title: '封神云防护系统' });
  const [showBackground, setShowBackground] = useState(false);
  const navigate = useNavigate();

  // 获取Bing每日壁纸
  const fetchBingWallpaper = async () => {
    try {
      const wallpaperData = await getWallpaperInfo();
      if (wallpaperData && wallpaperData.url) {
        setWallpaperUrl(wallpaperData.url);
        setWallpaperInfo(wallpaperData);
        // 设置加载完成状态
        setTimeout(() => {
          setWallpaperLoaded(true);
          setShowBackground(true);
        }, 100); // 短暂延迟确保图片加载
      } else {
        // 确保有默认背景
        setWallpaperUrl('https://picsum.photos/id/1039/1920/1080');
        setWallpaperLoaded(true);
        setShowBackground(true);
      }
    } catch (error) {
      console.error('获取Bing壁纸失败:', error);
      // 加载失败时使用备用图片
      setWallpaperUrl('https://picsum.photos/id/1039/1920/1080');
      setWallpaperLoaded(true);
      setShowBackground(true);
    } finally {
      setLoading(false);
    }
  };

  // 处理壁纸加载完成
  const handleWallpaperLoad = () => {
    setWallpaperLoaded(true);
    setShowBackground(true);
    setLoading(false);
  };

  useEffect(() => {
    fetchBingWallpaper();
  }, []);

  const onFinish = async (values) => {
    try {
      setLoading(true);
      const response = await login(values.username, values.password);
      
      if (response.data && response.data.code === 0) {
        message.success('登录成功！');
        // 存储token - 使用后端返回的access_token字段
        localStorage.setItem('token', response.data.data.access_token);
        localStorage.setItem('username', values.username);
        // 跳转到仪表盘
        navigate('/dashboard');
      } else {
        message.error(response.data?.message || '登录失败');
      }
    } catch (error) {
      console.error('登录错误:', error);
      message.error('登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* 加载指示器 */}
      <Spin 
        spinning={loading} 
        tip="加载中..."
        className="login-spin"
      >
        {/* 背景图容器 */}
        <div className="background-container">
          {wallpaperUrl && (
            <img 
              id="bing-wallpaper" 
              alt="Bing每日壁纸" 
              src={wallpaperUrl}
              onLoad={handleWallpaperLoad}
              onError={(e) => {
                console.error('壁纸加载失败，使用备用图片', e);
                setWallpaperUrl('https://picsum.photos/id/1039/1920/1080');
                setWallpaperLoaded(true);
                setShowBackground(true);
                setLoading(false);
              }}
              style={{ 
                opacity: wallpaperLoaded ? 1 : 0,
                display: 'block',
                zIndex: showBackground ? 1 : -2
              }}
            />
          )}
        </div>
        <div className="background-overlay" style={{ zIndex: showBackground ? 2 : -1 }}></div>
        
        {/* 登录卡片 */}
        <Badge.Ribbon text="安全登录" color="#52c41a">
          <Card 
            className="login-card"
            bordered={false}
          >
            <div className="login-header">
              <h1>{wallpaperInfo.title}</h1>
              <p>安全登录，智能防护</p>
            </div>
            
            <Form
              name="login"
              onFinish={onFinish}
              className="login-form"
              size="large"
              layout="vertical"
            >
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input
                  placeholder="请输入用户名"
                  prefix={<UserOutlined />}
                  size="large"
                />
              </Form.Item>
              
              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password
                  placeholder="请输入密码"
                  prefix={<LockOutlined />}
                  size="large"
                />
              </Form.Item>
              
              <Form.Item style={{ marginBottom: 0 }}>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  size="large"
                  icon={<SafetyOutlined />}
                  loading={loading}
                  style={{ width: '100%' }}
                >
                  登录
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Badge.Ribbon>
      </Spin>
    </div>
  );
};

export default Login;
