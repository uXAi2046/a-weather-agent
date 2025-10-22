"""
Weather MCP服务器
基于MCP协议的天气查询服务器实现
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, 
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource
)

from .services.weather_service import WeatherService
from .services.city_parser import CityParser
from .models.weather import WeatherResponse
from .models.city import CityInfo

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeatherMCPServer:
    """天气MCP服务器"""
    
    def __init__(self):
        """初始化服务器"""
        from config.settings import settings
        
        self.server = Server("weather-mcp")
        self.weather_service = WeatherService(settings.amap_api_key)
        self.city_parser = CityParser()
        
        # 注册工具和资源
        self._register_tools()
        self._register_resources()
        
    def _register_tools(self) -> None:
        """注册MCP工具"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="get_weather",
                    description="获取指定城市的天气信息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称，支持中文城市名"
                            },
                            "weather_type": {
                                "type": "string",
                                "enum": ["live", "forecast"],
                                "default": "live",
                                "description": "天气类型：live(实况天气) 或 forecast(预报天气)"
                            }
                        },
                        "required": ["city"]
                    }
                ),
                Tool(
                    name="search_city",
                    description="搜索城市信息，支持模糊匹配",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "城市搜索关键词"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "返回结果数量限制"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_weather_forecast",
                    description="获取指定城市的详细天气预报",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称"
                            },
                            "days": {
                                "type": "integer",
                                "default": 3,
                                "minimum": 1,
                                "maximum": 7,
                                "description": "预报天数（1-7天）"
                            }
                        },
                        "required": ["city"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """处理工具调用"""
            try:
                if name == "get_weather":
                    return await self._handle_get_weather(arguments)
                elif name == "search_city":
                    return await self._handle_search_city(arguments)
                elif name == "get_weather_forecast":
                    return await self._handle_get_weather_forecast(arguments)
                else:
                    raise ValueError(f"未知工具: {name}")
                    
            except Exception as e:
                logger.error(f"工具调用失败: {name}, 错误: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, ensure_ascii=False, indent=2)
                )]
    
    def _register_resources(self) -> None:
        """注册MCP资源"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="weather://cities",
                    name="城市列表",
                    description="支持的城市列表",
                    mimeType="application/json"
                ),
                Resource(
                    uri="weather://api-info",
                    name="API信息",
                    description="天气API使用信息和限制",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """读取资源内容"""
            if uri == "weather://cities":
                cities = await self.city_parser.get_all_cities()
                return json.dumps(cities[:100], ensure_ascii=False, indent=2)  # 限制返回数量
            elif uri == "weather://api-info":
                return json.dumps({
                    "api_provider": "高德地图",
                    "rate_limit": "每日1000次",
                    "supported_types": ["live", "forecast"],
                    "supported_regions": "中国大陆",
                    "cache_duration": "5分钟"
                }, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"未知资源: {uri}")
    
    async def _handle_get_weather(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理获取天气请求"""
        city = arguments.get("city")
        weather_type = arguments.get("weather_type", "live")
        
        if not city:
            raise ValueError("城市名称不能为空")
        
        logger.info(f"获取天气信息: 城市={city}, 类型={weather_type}")
        
        # 解析城市
        city_result = self.city_parser.parse_city_from_text(city)
        if not city_result.exact_match:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"未找到城市: {city}",
                    "suggestions": [city.dict() for city in city_result.fuzzy_matches[:5]]
                }, ensure_ascii=False, indent=2)
            )]
        
        city_info = city_result.exact_match
        
        # 获取天气信息
        if weather_type == "live":
            weather_data = await self.weather_service.get_live_weather(city_info.adcode)
        else:
            weather_data = await self.weather_service.get_forecast_weather(city_info.adcode)
        
        # 格式化响应
        response = {
            "city": city_info.dict(),
            "weather": weather_data,
            "timestamp": weather_data.get('timestamp') if weather_data else None
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, ensure_ascii=False, indent=2)
        )]
    
    async def _handle_search_city(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理城市搜索请求"""
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        
        if not query:
            raise ValueError("搜索关键词不能为空")
        
        logger.info(f"搜索城市: 关键词={query}, 限制={limit}")
        
        # 搜索城市
        cities = self.city_parser.search_cities(query, limit=limit)
        
        response = {
            "query": query,
            "count": len(cities),
            "cities": [city.dict() for city in cities]
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, ensure_ascii=False, indent=2)
        )]
    
    async def _handle_get_weather_forecast(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理天气预报请求"""
        city = arguments.get("city")
        days = arguments.get("days", 3)
        
        if not city:
            raise ValueError("城市名称不能为空")
        
        logger.info(f"获取天气预报: 城市={city}, 天数={days}")
        
        # 解析城市
        city_result = self.city_parser.parse_city_from_text(city)
        if not city_result.exact_match:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"未找到城市: {city}",
                    "suggestions": [city.dict() for city in city_result.fuzzy_matches[:5]]
                }, ensure_ascii=False, indent=2)
            )]
        
        city_info = city_result.exact_match
        
        # 获取预报天气
        weather_data = await self.weather_service.get_forecast_weather(city_info.adcode)
        
        # 处理预报数据，限制天数
        if weather_data and weather_data.get('weather') and weather_data['weather'].get('forecasts'):
            forecasts = weather_data['weather']['forecasts']
            if forecasts and len(forecasts) > 0:
                forecast_data = forecasts[0]
                if forecast_data.get('casts'):
                    forecast_data['casts'] = forecast_data['casts'][:days]
        
        response = {
            "city": city_info.dict(),
            "forecast": weather_data,
            "days_requested": days,
            "timestamp": weather_data.get('timestamp') if weather_data else None
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(response, ensure_ascii=False, indent=2)
        )]
    
    async def run(self) -> None:
        """运行MCP服务器"""
        logger.info("启动Weather MCP服务器...")
        
        # 初始化服务（如果有initialize方法的话）
        if hasattr(self.weather_service, 'initialize'):
            await self.weather_service.initialize()
        if hasattr(self.city_parser, 'initialize'):
            await self.city_parser.initialize()
        
        logger.info("Weather MCP服务器已启动，等待连接...")
        
        # 运行stdio服务器
        async with stdio_server() as (read_stream, write_stream):
            from mcp.types import ServerCapabilities
            
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="weather-mcp",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools={},
                        resources={}
                    )
                )
            )


async def main():
    """主函数"""
    try:
        server = WeatherMCPServer()
        await server.run()
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器运行错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())