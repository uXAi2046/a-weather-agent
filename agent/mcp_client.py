"""
MCP客户端模块
提供与Weather MCP服务器的连接和通信功能
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from utils.logger import get_logger

logger = get_logger(__name__)


class MCPClientError(Exception):
    """MCP客户端异常"""
    pass


class WeatherMCPClient:
    """天气MCP客户端
    
    负责与Weather MCP服务器建立连接，管理会话，并提供工具调用接口
    """
    
    def __init__(self, server_command: List[str], timeout: float = 30.0):
        """初始化MCP客户端
        
        Args:
            server_command: MCP服务器启动命令
            timeout: 连接超时时间（秒）
        """
        self.server_command = server_command
        self.timeout = timeout
        self.session: Optional[ClientSession] = None
        self._connected = False
        
    async def _create_session(self):
        """创建新的会话"""
        server_params = StdioServerParameters(
            command=self.server_command[0],
            args=self.server_command[1:] if len(self.server_command) > 1 else [],
            env=None
        )
        
        logger.info(f"启动MCP服务器: {' '.join(self.server_command)}")
        
        # 建立连接
        stdio_context = stdio_client(server_params)
        read, write = await stdio_context.__aenter__()
        
        session_context = ClientSession(read, write)
        session = await session_context.__aenter__()
        
        # 初始化会话
        server_info = await session.initialize()
        logger.info(f"服务器信息: {server_info}")
        
        # 列出可用工具
        tools_result = await session.list_tools()
        logger.info(f"可用工具: {[tool.name for tool in tools_result.tools]}")
        
        return session, session_context, stdio_context
        
    async def connect(self) -> None:
        """连接到MCP服务器"""
        if self._connected:
            return
        
        try:
            self.session, self._session_context, self._stdio_context = await self._create_session()
            self._connected = True
            logger.info("MCP服务器连接成功")
                    
        except Exception as e:
            logger.error(f"连接MCP服务器失败: {e}")
            raise MCPClientError(f"连接失败: {e}")
    
    async def disconnect(self) -> None:
        """断开与MCP服务器的连接"""
        if self._connected:
            try:
                self._connected = False
                
                if self._session_context:
                    try:
                        await self._session_context.__aexit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"关闭会话上下文时出错: {e}")
                    self._session_context = None
                    
                if self._stdio_context:
                    try:
                        await self._stdio_context.__aexit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"关闭stdio上下文时出错: {e}")
                    self._stdio_context = None
                    
                self.session = None
                logger.info("已断开MCP服务器连接")
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
            
        Raises:
            MCPClientError: 工具调用失败
        """
        if not self.session or not self._connected:
            raise MCPClientError("未连接到MCP服务器")
        
        try:
            logger.debug(f"调用工具: {tool_name}, 参数: {arguments}")
            
            # 调用工具
            result = await self.session.call_tool(tool_name, arguments)
            
            logger.debug(f"工具调用结果: {result}")
            
            # 处理返回结果
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    # 尝试解析JSON
                    try:
                        import json
                        return json.loads(content.text)
                    except (json.JSONDecodeError, TypeError):
                        return {"result": content.text}
                else:
                    return {"result": str(content)}
            else:
                return {"error": "工具调用无返回内容"}
            
        except Exception as e:
            logger.error(f"工具调用失败: {tool_name}, 错误: {e}")
            raise MCPClientError(f"工具调用失败: {e}")
    
    async def get_weather(self, city: str, weather_type: str = "live") -> Dict[str, Any]:
        """获取天气信息
        
        Args:
            city: 城市名称
            weather_type: 天气类型 ("live" 或 "forecast")
            
        Returns:
            天气信息
        """
        return await self.call_tool("get_weather", {
            "city": city,
            "weather_type": weather_type
        })
    
    async def search_city(self, query: str) -> List[Dict[str, Any]]:
        """搜索城市
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的城市列表
        """
        result = await self.call_tool("search_city", {"query": query})
        return result if isinstance(result, list) else []
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self.session is not None


class MCPClientManager:
    """MCP客户端管理器
    
    提供连接池和自动重连功能
    """
    
    def __init__(self, server_command: List[str], max_retries: int = 3):
        """初始化客户端管理器
        
        Args:
            server_command: MCP服务器启动命令
            max_retries: 最大重试次数
        """
        self.server_command = server_command
        self.max_retries = max_retries
        self.client: Optional[WeatherMCPClient] = None
        
    @asynccontextmanager
    async def get_client(self):
        """获取MCP客户端（上下文管理器）"""
        client = None
        try:
            client = await self._ensure_connected()
            yield client
        except Exception as e:
            logger.error(f"客户端操作失败: {e}")
            raise
        finally:
            if client:
                await client.disconnect()
    
    async def _ensure_connected(self) -> WeatherMCPClient:
        """确保客户端已连接"""
        for attempt in range(self.max_retries):
            try:
                client = WeatherMCPClient(self.server_command)
                await client.connect()
                return client
            except Exception as e:
                logger.warning(f"连接尝试 {attempt + 1}/{self.max_retries} 失败: {e}")
                if attempt == self.max_retries - 1:
                    raise MCPClientError(f"连接失败，已重试 {self.max_retries} 次")
                await asyncio.sleep(1)  # 等待1秒后重试
        
        raise MCPClientError("无法建立连接")


# 便捷函数
async def create_weather_client(server_command: List[str]) -> WeatherMCPClient:
    """创建并连接天气MCP客户端
    
    Args:
        server_command: MCP服务器启动命令
        
    Returns:
        已连接的MCP客户端
    """
    client = WeatherMCPClient(server_command)
    await client.connect()
    return client


# 示例使用
async def main():
    """示例用法"""
    server_cmd = ["python", "-m", "weather_mcp.server"]
    
    try:
        # 方式1: 直接使用客户端
        client = await create_weather_client(server_cmd)
        
        # 获取天气信息
        weather = await client.get_weather("北京", "live")
        print(f"天气信息: {weather}")
        
        # 搜索城市
        cities = await client.search_city("上海")
        print(f"城市搜索结果: {cities}")
        
        await client.disconnect()
        
        # 方式2: 使用管理器
        manager = MCPClientManager(server_cmd)
        async with manager.get_client() as client:
            weather = await client.get_weather("广州", "forecast")
            print(f"预报天气: {weather}")
            
    except MCPClientError as e:
        print(f"MCP客户端错误: {e}")
    except Exception as e:
        print(f"未知错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())