/**
 * 数据验证工具函数
 */

/**
 * 确保数据是数组格式
 * @param {any} data - 要验证的数据
 * @param {Array} defaultValue - 默认值
 * @returns {Array} 数组数据
 */
export const ensureArray = (data, defaultValue = []) => {
  if (Array.isArray(data)) {
    return data;
  }
  if (data && typeof data === 'object' && data.data && Array.isArray(data.data)) {
    return data.data;
  }
  return defaultValue;
};

/**
 * 确保数据是对象格式
 * @param {any} data - 要验证的数据
 * @param {Object} defaultValue - 默认值
 * @returns {Object} 对象数据
 */
export const ensureObject = (data, defaultValue = {}) => {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return data;
  }
  return defaultValue;
};

/**
 * 安全地获取嵌套对象属性
 * @param {Object} obj - 对象
 * @param {string} path - 属性路径
 * @param {any} defaultValue - 默认值
 * @returns {any} 属性值
 */
export const safeGet = (obj, path, defaultValue = null) => {
  if (!obj || typeof obj !== 'object') {
    return defaultValue;
  }
  
  const keys = path.split('.');
  let result = obj;
  
  for (const key of keys) {
    if (result && typeof result === 'object' && key in result) {
      result = result[key];
    } else {
      return defaultValue;
    }
  }
  
  return result;
};
