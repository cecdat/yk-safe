import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Spin, message } from 'antd';
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
  const navigate = useNavigate();

  // 获取Bing每日壁纸
  const fetchBingWallpaper = async () => {
    try {
      const wallpaperData = await getWallpaperInfo();
      setWallpaperUrl(wallpaperData.url);
      setWallpaperInfo(wallpaperData);
    } catch (error) {
      console.error('获取Bing壁纸失败:', error);
      // 加载失败时使用备用图片
      setWallpaperUrl('https://picsum.photos/id/1059/1920/1080');
    }
  };

  // 处理壁纸加载完成
  const handleWallpaperLoad = () => {
    setWallpaperLoaded(true);
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
              style={{ opacity: wallpaperLoaded ? 1 : 0 }}
            />
          )}
        </div>
        <div className="background-overlay"></div>
        
        {/* 登录卡片 */}
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
          >
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input
                placeholder="请输入用户名"
                prefix={<UserOutlined />}
                className="form-control"
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
                className="form-control"
              />
            </Form.Item>
            
            <Form.Item>
              <Button 
                type="primary" 
                htmlType="submit"
                className="btn-login"
                icon={<SafetyOutlined />}
                loading={loading}
              >
                登录
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Spin>
    </div>
  );
};

export default Login;
