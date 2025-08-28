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

// 系统信息相关API
export const getSystemInfo = () => {
  return api.get('/monitor/system');
};

export const getNetworkInfo = () => {
  return api.get('/monitor/network');
};

export const getProcessInfo = () => {
  return api.get('/monitor/processes');
};

export const getFirewallStatus = () => {
  return api.get('/monitor/firewall-status');
};

// 网络连接相关API
export const getNetworkConnections = () => {
  return api.get('/monitor/connections');
};

export const getIpConnectionDetails = (ip) => {
  return api.get(`/monitor/connections/${ip}`);
};
