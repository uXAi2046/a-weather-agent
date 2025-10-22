"""
高德地图天气API客户端
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from loguru import logger

from ..models.weather import WeatherResponse, WeatherQuery, WeatherError


class AmapWeatherClient:
    """高德地图天气API客户端"""
    
    BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        初始化高德天气客户端
        
        Args:
            api_key: 高德地图API密钥
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._client:
            await self._client.aclose()
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发起HTTP请求
        
        Args:
            params: 请求参数
            
        Returns:
            响应数据
            
        Raises:
            WeatherError: 请求失败时抛出
        """
        try:
            client = self._get_client()
            
            # 添加API密钥
            params["key"] = self.api_key
            
            logger.debug(f"发起天气API请求: {self.BASE_URL}, 参数: {params}")
            
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug(f"天气API响应: {data}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP请求失败: {e}")
            raise WeatherError(f"HTTP请求失败: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"网络请求错误: {e}")
            raise WeatherError(f"网络请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"请求处理异常: {e}")
            raise WeatherError(f"请求处理异常: {str(e)}")
    
    async def get_weather(self, query: WeatherQuery) -> WeatherResponse:
        """
        获取天气信息
        
        Args:
            query: 天气查询请求
            
        Returns:
            天气响应数据
            
        Raises:
            WeatherError: 请求失败或数据解析失败时抛出
        """
        try:
            # 构建请求参数
            params = {
                "city": query.city,
                "extensions": query.extensions,
                "output": query.output
            }
            
            # 发起请求
            data = await self._make_request(params)
            
            # 解析响应
            weather_response = WeatherResponse(**data)
            
            # 检查响应状态
            if not weather_response.is_success:
                error_msg = f"API返回错误: {weather_response.info} (状态码: {weather_response.infocode})"
                logger.error(error_msg)
                raise WeatherError(
                    error_msg,
                    status=weather_response.status,
                    infocode=weather_response.infocode
                )
            
            logger.info(f"成功获取天气数据: 城市={query.city}, 类型={query.extensions}")
            return weather_response
            
        except WeatherError:
            raise
        except Exception as e:
            logger.error(f"天气数据解析失败: {e}")
            raise WeatherError(f"天气数据解析失败: {str(e)}")
    
    async def get_live_weather(self, city: str) -> WeatherResponse:
        """
        获取实时天气
        
        Args:
            city: 城市名称或adcode
            
        Returns:
            实时天气响应
        """
        query = WeatherQuery(city=city, extensions="base")
        return await self.get_weather(query)
    
    async def get_forecast_weather(self, city: str) -> WeatherResponse:
        """
        获取天气预报
        
        Args:
            city: 城市名称或adcode
            
        Returns:
            天气预报响应
        """
        query = WeatherQuery(city=city, extensions="all")
        return await self.get_weather(query)
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None


class AmapWeatherClientSync:
    """高德地图天气API同步客户端"""
    
    def __init__(self, api_key: str, timeout: int = 30):
        """
        初始化高德天气同步客户端
        
        Args:
            api_key: 高德地图API密钥
            timeout: 请求超时时间（秒）
        """
        self.async_client = AmapWeatherClient(api_key, timeout)
    
    def get_weather(self, query: WeatherQuery) -> WeatherResponse:
        """
        获取天气信息（同步版本）
        
        Args:
            query: 天气查询请求
            
        Returns:
            天气响应数据
        """
        return asyncio.run(self.async_client.get_weather(query))
    
    def get_live_weather(self, city: str) -> WeatherResponse:
        """
        获取实时天气（同步版本）
        
        Args:
            city: 城市名称或adcode
            
        Returns:
            实时天气响应
        """
        return asyncio.run(self.async_client.get_live_weather(city))
    
    def get_forecast_weather(self, city: str) -> WeatherResponse:
        """
        获取天气预报（同步版本）
        
        Args:
            city: 城市名称或adcode
            
        Returns:
            天气预报响应
        """
        return asyncio.run(self.async_client.get_forecast_weather(city))