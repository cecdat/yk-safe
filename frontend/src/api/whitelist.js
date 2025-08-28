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

// Token管理
export const getWhitelistTokens = () => {
  return api.get('/whitelist/tokens');
};

export const createWhitelistToken = (data) => {
  return api.post('/whitelist/tokens', data);
};

export const updateWhitelistToken = (id, data) => {
  return api.put(`/whitelist/tokens/${id}`, data);
};

export const deleteWhitelistToken = (id) => {
  return api.delete(`/whitelist/tokens/${id}`);
};

// 申请管理
export const getWhitelistRequests = (params) => {
  return api.get('/whitelist/requests', { params });
};

export const getWhitelistRequest = (id) => {
  return api.get(`/whitelist/requests/${id}`);
};

export const approveWhitelistRequest = (id, data) => {
  return api.put(`/whitelist/requests/${id}/approve`, data);
};

// 公开接口
export const createPublicWhitelistRequest = (data) => {
  return api.post('/whitelist/public/request', data);
};

export const getPublicIp = () => {
  return api.get('/whitelist/public/ip');
};

export const checkProxy = () => {
  return api.get('/whitelist/public/proxy-check');
};
