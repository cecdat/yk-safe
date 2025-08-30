// external.js - 外部API服务

// 获取Bing每日壁纸
export const getBingWallpaper = async () => {
  try {
    // 使用更稳定的Bing壁纸API
    const response = await fetch('https://bing.biturl.top/?resolution=1920&format=json&index=0&mkt=zh-CN');
    
    if (!response.ok) {
      throw new Error('网络响应不正常');
    }
    
    const data = await response.json();
    return {
      url: data.url,
      title: data.title || '封神云防护系统',
      copyright: data.copyright || 'Bing',
      copyrightLink: data.copyrightlink || '#'
    };
  } catch (error) {
    console.error('获取Bing壁纸失败:', error);
    throw error;
  }
};

// 获取备用壁纸
export const getFallbackWallpaper = async () => {
  try {
    // 使用更稳定的备用图片源
    const randomId = Math.floor(Math.random() * 1000);
    const fallbackUrl = `https://picsum.photos/id/${randomId}/1920/1080`;
    return {
      url: fallbackUrl,
      title: '封神云防护系统',
      copyright: 'Unsplash',
      copyrightLink: 'https://unsplash.com'
    };
  } catch (error) {
    console.error('获取备用壁纸失败:', error);
    throw error;
  }
};

// 获取壁纸信息（主要函数）
export const getWallpaperInfo = async () => {
  try {
    // 优先尝试Bing壁纸
    const bingResult = await Promise.race([
      getBingWallpaper(),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Bing壁纸请求超时')), 5000))
    ]);
    return bingResult;
  } catch (error) {
    console.warn('Bing壁纸获取失败或超时，使用备用壁纸:', error.message);
    try {
      // 备用方案：Unsplash随机壁纸
      return await getFallbackWallpaper();
    } catch (fallbackError) {
      console.error('所有壁纸获取失败:', fallbackError);
      // 最终备用：使用本地预定义的图片地址，确保始终有背景图显示
      return {
        url: 'https://picsum.photos/id/1039/1920/1080', // 固定使用一个ID的图片作为最终备用
        title: '封神云防护系统',
        copyright: 'YK-Safe',
        copyrightLink: '#'
      };
    }
  }
};
