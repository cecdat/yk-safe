import axios from 'axios';

// 创建axios实例
const api = axios.create({
  timeout: 10000,
});

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.warn('External API request failed:', error);
    return Promise.reject(error);
  }
);

// Bing 每日壁纸 API
export const getBingWallpaper = async () => {
  try {
    // 使用 CORS 代理来避免跨域问题
    const corsProxy = 'https://api.allorigins.win/raw?url=';
    const bingApiUrl = 'https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=en-US';
    
    const response = await api.get(`${corsProxy}${encodeURIComponent(bingApiUrl)}`);
    
    if (response.data && response.data.images && response.data.images.length > 0) {
      const image = response.data.images[0];
      return {
        url: `https://www.bing.com${image.url}`,
        title: image.title || 'Bing Daily Wallpaper',
        copyright: image.copyright || 'Microsoft Bing',
        copyrightLink: image.copyrightlink || 'https://www.bing.com',
        startDate: image.startdate,
        endDate: image.enddate,
        fullStartDate: image.fullstartdate
      };
    }
    
    throw new Error('No wallpaper data available');
  } catch (error) {
    console.warn('Failed to fetch Bing wallpaper:', error);
    throw error;
  }
};

// 备用壁纸 API（如果 Bing API 失败）
export const getFallbackWallpaper = async () => {
  try {
    // 使用 Unsplash 随机壁纸作为备用
    const response = await api.get('https://source.unsplash.com/1920x1080/?nature,landscape');
    
    return {
      url: response.request.responseURL,
      title: 'Nature Landscape',
      copyright: 'Unsplash',
      copyrightLink: 'https://unsplash.com',
      startDate: new Date().toISOString().split('T')[0],
      endDate: new Date().toISOString().split('T')[0],
      fullStartDate: new Date().toISOString()
    };
  } catch (error) {
    console.warn('Failed to fetch fallback wallpaper:', error);
    throw error;
  }
};

// 获取壁纸信息（主函数）
export const getWallpaperInfo = async () => {
  try {
    // 优先尝试 Bing 壁纸
    return await getBingWallpaper();
  } catch (error) {
    try {
      // 如果 Bing 失败，使用备用壁纸
      return await getFallbackWallpaper();
    } catch (fallbackError) {
      // 如果都失败，返回默认信息
      console.warn('All wallpaper APIs failed, using default');
      return {
        url: null,
        title: 'Default Background',
        copyright: 'YK-Safe',
        copyrightLink: '#',
        startDate: new Date().toISOString().split('T')[0],
        endDate: new Date().toISOString().split('T')[0],
        fullStartDate: new Date().toISOString()
      };
    }
  }
};
