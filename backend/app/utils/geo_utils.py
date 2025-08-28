import os
import geoip2.database
import geoip2.errors
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GeoIPManager:
    """IP地理位置查询管理器"""
    
    def __init__(self):
        self.reader = None
        self.db_path = os.path.join(os.path.dirname(__file__), 'GeoLite2-City.mmdb')
        self._init_database()
    
    def _init_database(self):
        """初始化GeoIP数据库"""
        try:
            if os.path.exists(self.db_path):
                self.reader = geoip2.database.Reader(self.db_path)
                logger.info(f"GeoIP数据库加载成功: {self.db_path}")
            else:
                logger.warning(f"GeoIP数据库文件不存在: {self.db_path}")
                self.reader = None
        except Exception as e:
            logger.error(f"加载GeoIP数据库失败: {e}")
            self.reader = None
    
    def get_ip_info(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """
        获取IP地址的地理位置信息
        
        Args:
            ip_address: IP地址
            
        Returns:
            包含地理位置信息的字典，如果查询失败返回None
        """
        if not self.reader:
            logger.warning("GeoIP数据库未初始化")
            return None
        
        try:
            # 查询IP信息
            response = self.reader.city(ip_address)
            
            # 构建返回信息
            ip_info = {
                'ip': ip_address,
                'country': {
                    'name': response.country.name,
                    'code': response.country.iso_code,
                    'names': response.country.names
                },
                'city': {
                    'name': response.city.name,
                    'names': response.city.names
                },
                'location': {
                    'latitude': response.location.latitude,
                    'longitude': response.location.longitude,
                    'timezone': response.location.time_zone
                },
                'subdivisions': [],
                'postal_code': response.postal.code,
                'continent': {
                    'name': response.continent.name,
                    'code': response.continent.code
                }
            }
            
            # 添加行政区信息
            if response.subdivisions.most_specific:
                ip_info['subdivisions'].append({
                    'name': response.subdivisions.most_specific.name,
                    'code': response.subdivisions.most_specific.iso_code
                })
            
            logger.debug(f"IP {ip_address} 地理位置信息: {ip_info}")
            return ip_info
            
        except geoip2.errors.AddressNotFoundError:
            logger.debug(f"IP地址 {ip_address} 在数据库中未找到")
            return None
        except geoip2.errors.InvalidDatabaseError as e:
            logger.error(f"GeoIP数据库无效: {e}")
            return None
        except Exception as e:
            logger.error(f"查询IP {ip_address} 地理位置信息时出错: {e}")
            return None
    
    def get_simple_ip_info(self, ip_address: str) -> Optional[Dict[str, str]]:
        """
        获取简化的IP地理位置信息
        
        Args:
            ip_address: IP地址
            
        Returns:
            简化的地理位置信息字典
        """
        ip_info = self.get_ip_info(ip_address)
        if not ip_info:
            return None
        
        return {
            'ip': ip_address,
            'country': ip_info['country']['name'] or '未知',
            'city': ip_info['city']['name'] or '未知',
            'region': ip_info['subdivisions'][0]['name'] if ip_info['subdivisions'] else '未知',
            'timezone': ip_info['location']['timezone'] or '未知'
        }
    
    def get_ip_summary(self, ip_address: str) -> str:
        """
        获取IP地址的地理位置摘要信息
        
        Args:
            ip_address: IP地址
            
        Returns:
            格式化的地理位置摘要字符串
        """
        ip_info = self.get_simple_ip_info(ip_address)
        if not ip_info:
            return f"{ip_address} (位置未知)"
        
        location_parts = []
        if ip_info['city'] and ip_info['city'] != '未知':
            location_parts.append(ip_info['city'])
        if ip_info['region'] and ip_info['region'] != '未知':
            location_parts.append(ip_info['region'])
        if ip_info['country'] and ip_info['country'] != '未知':
            location_parts.append(ip_info['country'])
        
        if location_parts:
            return f"{ip_address} ({', '.join(location_parts)})"
        else:
            return f"{ip_address} (位置未知)"
    
    def close(self):
        """关闭数据库连接"""
        if self.reader:
            self.reader.close()
            logger.info("GeoIP数据库连接已关闭")

# 创建全局实例
geoip_manager = GeoIPManager()

def get_ip_location(ip_address: str) -> Optional[Dict[str, Any]]:
    """获取IP地址的地理位置信息（便捷函数）"""
    return geoip_manager.get_ip_info(ip_address)

def get_ip_location_simple(ip_address: str) -> Optional[Dict[str, str]]:
    """获取简化的IP地理位置信息（便捷函数）"""
    return geoip_manager.get_simple_ip_info(ip_address)

def get_ip_location_summary(ip_address: str) -> str:
    """获取IP地址的地理位置摘要（便捷函数）"""
    return geoip_manager.get_ip_summary(ip_address)
