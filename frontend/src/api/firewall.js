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
    // 确保返回的数据格式正确
    if (response.data && response.data.code === 0) {
      return response.data;
    }
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

// 防火墙相关API
export const getFirewallStatus = () => {
  return api.get('/firewall/status');
};

export const startFirewall = () => {
  return api.post('/firewall/start');
};

export const stopFirewall = () => {
  return api.post('/firewall/stop');
};

export const restartFirewall = () => {
  return api.post('/firewall/restart');
};

export const getFirewallRules = () => {
  return api.get('/firewall/rules');
};

export const addFirewallRule = (rule) => {
  return api.post('/firewall/rules', rule);
};

export const updateFirewallRule = (ruleId, rule) => {
  return api.put(`/firewall/rules/${ruleId}`, rule);
};

export const deleteFirewallRule = (ruleId) => {
  return api.delete(`/firewall/rules/${ruleId}`);
};

export const getBlacklistCount = () => {
  return api.get('/blacklist/count');
};

export const getSystemLogs = (params = {}) => {
  return api.get('/logs/system', { params });
};

export const getFirewallLogs = (params = {}) => {
  return api.get('/logs/firewall', { params });
};

export const getFirewallLogSummary = (hours = 24) => {
  return api.get('/logs/firewall/summary', { params: { hours } });
};

export const cleanupFirewallLogs = (days = 30) => {
  return api.post('/logs/firewall/cleanup', null, { params: { days } });
};

export const exportFirewallLogs = (days = 7, format = 'csv') => {
  return api.get('/logs/firewall/export', { params: { days, format } });
};

export const getLogStats = () => {
  return api.get('/logs/stats');
};

export const getFirewallConfig = () => {
  return api.get('/firewall/config');
};

export const updateFirewallMode = (mode, description) => {
  return api.put('/firewall/config/mode', { mode, description });
};
