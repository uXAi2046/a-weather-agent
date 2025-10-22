"""
天气服务核心模块
集成城市解析和天气API调用
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
from loguru import logger

from ..models.weather import WeatherQuery, LiveWeather, ForecastWeather, WeatherError
from ..models.city import CityInfo, CitySearchResult
from ..clients.amap_client import AmapWeatherClient
from ..services.city_parser import CityParser


class WeatherService:
    """天气服务核心类"""
    
    def __init__(self, 
                 amap_api_key: str,
                 city_parser: Optional[CityParser] = None,
                 weather_client: Optional[AmapWeatherClient] = None):
        """
        初始化天气服务
        
        Args:
            amap_api_key: 高德地图API密钥
            city_parser: 城市解析器
            weather_client: 天气API客户端
        """
        self.amap_api_key = amap_api_key
        self.city_parser = city_parser or CityParser()
        self.weather_client = weather_client or AmapWeatherClient(amap_api_key)
        
        # 缓存配置
        self.cache_enabled = True
        self.live_cache_ttl = 600  # 实时天气缓存10分钟
        self.forecast_cache_ttl = 3600  # 预报天气缓存1小时
        
        # 内存缓存
        self._live_cache: Dict[str, Dict[str, Any]] = {}
        self._forecast_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info("天气服务初始化完成")
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any], ttl: int) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cache_entry: 缓存条目
            ttl: 生存时间（秒）
            
        Returns:
            缓存是否有效
        """
        if not cache_entry or 'timestamp' not in cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cache_time < timedelta(seconds=ttl)
    
    def _get_from_cache(self, cache_dict: Dict[str, Dict[str, Any]], 
                       key: str, ttl: int) -> Optional[Any]:
        """
        从缓存获取数据
        
        Args:
            cache_dict: 缓存字典
            key: 缓存键
            ttl: 生存时间
            
        Returns:
            缓存的数据或None
        """
        if not self.cache_enabled or key not in cache_dict:
            return None
        
        cache_entry = cache_dict[key]
        if self._is_cache_valid(cache_entry, ttl):
            logger.debug(f"缓存命中: {key}")
            return cache_entry['data']
        else:
            # 清理过期缓存
            del cache_dict[key]
            logger.debug(f"缓存过期: {key}")
            return None
    
    def _set_to_cache(self, cache_dict: Dict[str, Dict[str, Any]], 
                     key: str, data: Any) -> None:
        """
        设置缓存数据
        
        Args:
            cache_dict: 缓存字典
            key: 缓存键
            data: 要缓存的数据
        """
        if not self.cache_enabled:
            return
        
        cache_dict[key] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        logger.debug(f"缓存设置: {key}")
    
    def parse_city_from_query(self, query: str) -> CitySearchResult:
        """
        从查询文本中解析城市信息
        
        Args:
            query: 查询文本
            
        Returns:
            城市搜索结果
        """
        try:
            result = self.city_parser.parse_city_from_text(query)
            logger.info(f"城市解析成功: 查询='{query}', 匹配数={len(result.matched_cities)}")
            return result
        except Exception as e:
            logger.error(f"城市解析失败: {e}")
            raise WeatherError(f"城市解析失败: {e}")
    
    async def get_live_weather(self, city_query: str) -> Dict[str, Any]:
        """
        获取实时天气
        
        Args:
            city_query: 城市查询（名称或adcode）
            
        Returns:
            天气数据字典
        """
        try:
            # 解析城市
            city_result = self.parse_city_from_query(city_query)
            
            if not city_result.exact_match and not city_result.matched_cities:
                raise WeatherError(f"未找到城市: {city_query}")
            
            # 选择最佳匹配城市
            target_city = city_result.exact_match or city_result.matched_cities[0]
            
            # 检查缓存
            cache_key = f"live_{target_city.adcode}"
            cached_data = self._get_from_cache(self._live_cache, cache_key, self.live_cache_ttl)
            if cached_data:
                return cached_data
            
            # 调用API获取天气数据
            weather_data = await self.weather_client.get_live_weather(target_city.adcode)
            
            # 构建返回数据
            result = {
                'city': {
                    'name': target_city.name,
                    'adcode': target_city.adcode,
                    'citycode': target_city.citycode
                },
                'weather': weather_data.dict() if weather_data else None,
                'query_info': {
                    'original_query': city_query,
                    'exact_match': city_result.exact_match is not None,
                    'alternative_cities': [
                        {'name': city.name, 'adcode': city.adcode} 
                        for city in city_result.fuzzy_matches[:3]
                    ] if city_result.fuzzy_matches else []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存结果
            self._set_to_cache(self._live_cache, cache_key, result)
            
            logger.info(f"实时天气获取成功: {target_city.name}")
            return result
            
        except Exception as e:
            logger.error(f"获取实时天气失败: {e}")
            raise WeatherError(f"获取实时天气失败: {e}")
    
    async def get_forecast_weather(self, city_query: str) -> Dict[str, Any]:
        """
        获取天气预报
        
        Args:
            city_query: 城市查询（名称或adcode）
            
        Returns:
            天气预报数据字典
        """
        try:
            # 解析城市
            city_result = self.parse_city_from_query(city_query)
            
            if not city_result.exact_match and not city_result.matched_cities:
                raise WeatherError(f"未找到城市: {city_query}")
            
            # 选择最佳匹配城市
            target_city = city_result.exact_match or city_result.matched_cities[0]
            
            # 检查缓存
            cache_key = f"forecast_{target_city.adcode}"
            cached_data = self._get_from_cache(self._forecast_cache, cache_key, self.forecast_cache_ttl)
            if cached_data:
                return cached_data
            
            # 调用API获取天气预报数据
            forecast_data = await self.weather_client.get_forecast_weather(target_city.adcode)
            
            # 构建返回数据
            result = {
                'city': {
                    'name': target_city.name,
                    'adcode': target_city.adcode,
                    'citycode': target_city.citycode
                },
                'forecast': forecast_data.dict() if forecast_data else None,
                'query_info': {
                    'original_query': city_query,
                    'exact_match': city_result.exact_match is not None,
                    'alternative_cities': [
                        {'name': city.name, 'adcode': city.adcode} 
                        for city in city_result.fuzzy_matches[:3]
                    ] if city_result.fuzzy_matches else []
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 缓存结果
            self._set_to_cache(self._forecast_cache, cache_key, result)
            
            logger.info(f"天气预报获取成功: {target_city.name}")
            return result
            
        except Exception as e:
            logger.error(f"获取天气预报失败: {e}")
            raise WeatherError(f"获取天气预报失败: {e}")
    
    async def get_weather_by_adcode(self, adcode: str, include_forecast: bool = True) -> Dict[str, Any]:
        """
        根据adcode获取天气信息
        
        Args:
            adcode: 行政区划代码
            include_forecast: 是否包含预报信息
            
        Returns:
            完整天气信息
        """
        try:
            # 获取城市信息
            city = self.city_parser.get_city_by_adcode(adcode)
            if not city:
                raise WeatherError(f"未找到adcode对应的城市: {adcode}")
            
            # 并发获取实时天气和预报
            tasks = [self.weather_client.get_live_weather(adcode)]
            if include_forecast:
                tasks.append(self.weather_client.get_forecast_weather(adcode))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            live_weather = results[0] if not isinstance(results[0], Exception) else None
            forecast_weather = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
            
            return {
                'city': {
                    'name': city.name,
                    'adcode': city.adcode,
                    'citycode': city.citycode
                },
                'live_weather': live_weather.dict() if live_weather else None,
                'forecast_weather': forecast_weather.dict() if forecast_weather else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"根据adcode获取天气失败: {e}")
            raise WeatherError(f"根据adcode获取天气失败: {e}")
    
    def search_cities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索城市
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            
        Returns:
            城市列表
        """
        try:
            cities = self.city_parser.search_cities(query, limit)
            return [
                {
                    'name': city.name,
                    'adcode': city.adcode,
                    'citycode': city.citycode,
                    'center': city.center,
                    'level': city.level
                }
                for city in cities
            ]
        except Exception as e:
            logger.error(f"搜索城市失败: {e}")
            raise WeatherError(f"搜索城市失败: {e}")
    
    def get_city_suggestions(self, partial_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取城市名称建议
        
        Args:
            partial_name: 部分城市名称
            limit: 建议数量限制
            
        Returns:
            城市建议列表
        """
        try:
            suggestions = self.city_parser.suggest_cities(partial_name, limit)
            return [
                {
                    'name': city.name,
                    'adcode': city.adcode,
                    'citycode': city.citycode
                }
                for city in suggestions
            ]
        except Exception as e:
            logger.error(f"获取城市建议失败: {e}")
            raise WeatherError(f"获取城市建议失败: {e}")
    
    def clear_cache(self) -> None:
        """清理所有缓存"""
        self._live_cache.clear()
        self._forecast_cache.clear()
        logger.info("缓存已清理")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        return {
            'live_cache_size': len(self._live_cache),
            'forecast_cache_size': len(self._forecast_cache),
            'cache_enabled': self.cache_enabled,
            'live_cache_ttl': self.live_cache_ttl,
            'forecast_cache_ttl': self.forecast_cache_ttl
        }


class WeatherServiceSync:
    """天气服务同步包装器"""
    
    def __init__(self, weather_service: WeatherService):
        """
        初始化同步包装器
        
        Args:
            weather_service: 异步天气服务实例
        """
        self.weather_service = weather_service
    
    def get_live_weather(self, city_query: str) -> Dict[str, Any]:
        """同步获取实时天气"""
        return asyncio.run(self.weather_service.get_live_weather(city_query))
    
    def get_forecast_weather(self, city_query: str) -> Dict[str, Any]:
        """同步获取天气预报"""
        return asyncio.run(self.weather_service.get_forecast_weather(city_query))
    
    def get_weather_by_adcode(self, adcode: str, include_forecast: bool = True) -> Dict[str, Any]:
        """同步根据adcode获取天气"""
        return asyncio.run(self.weather_service.get_weather_by_adcode(adcode, include_forecast))
    
    def search_cities(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """同步搜索城市"""
        return self.weather_service.search_cities(query, limit)
    
    def get_city_suggestions(self, partial_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """同步获取城市建议"""
        return self.weather_service.get_city_suggestions(partial_name, limit)