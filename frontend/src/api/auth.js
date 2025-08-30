import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 登录API
export const login = async (username, password) => {
  return api.post('/auth/login', {
    username,
    password
  });
};

// 登出API
export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  window.location.href = '/login';
};

// 检查登录状态
export const checkAuth = () => {
  const token = localStorage.getItem('token');
  return !!token;
};

// 获取当前用户信息
export const getCurrentUser = () => {
  const username = localStorage.getItem('username');
  return username ? { username } : null;
};
