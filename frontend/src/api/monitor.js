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

export const getContainerInfo = () => {
  return api.get('/monitor/containers');
};

// 网络连接相关API
export const getNetworkConnections = () => {
  return api.get('/monitor/connections');
};

export const getIpConnectionDetails = (ip) => {
  return api.get(`/monitor/connections/${ip}`);
};

// 防火墙状态相关API（监控视角）
export const getFirewallStatus = () => {
  return api.get('/firewall/status');
};

export const getFirewallConfig = () => {
  return api.get('/firewall/config');
};

// 仪表盘综合数据API - 推荐使用，性能更好
export const getDashboardData = () => {
  return api.get('/monitor/dashboard');
};

// 实时监控数据API
export const getRealTimeStats = () => {
  return api.get('/monitor/realtime');
};

// 历史监控数据API
export const getHistoricalStats = (hours = 24) => {
  return api.get('/monitor/historical', { params: { hours } });
};
