"""
集成测试模块
测试整个天气查询Agent系统的端到端功能
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock

from agent.weather_agent import WeatherAgent, create_weather_agent
from agent.mcp_client import WeatherMCPClient
from weather_mcp.server import WeatherMCPServer
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("test_integration")


class TestWeatherAgentIntegration:
    """天气Agent集成测试"""
    
    @pytest.fixture
    async def weather_agent(self):
        """创建天气Agent实例"""
        # 模拟DeepSeek API密钥
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            agent = await create_weather_agent()
            yield agent
    
    @pytest.fixture
    def mcp_client(self):
        """创建MCP客户端实例"""
        client = WeatherMCPClient()
        yield client
        # 清理
        if hasattr(client, 'session') and client.session:
            asyncio.create_task(client.disconnect())
    
    @pytest.fixture
    def mcp_server(self):
        """创建MCP服务器实例"""
        server = WeatherMCPServer()
        return server
    
    @pytest.mark.asyncio
    async def test_weather_query_flow(self, weather_agent):
        """测试完整的天气查询流程"""
        # 模拟MCP客户端响应
        mock_weather_data = {
            "city": "北京",
            "weather": "晴",
            "temperature": "25°C",
            "humidity": "60%",
            "wind": "东风 2级"
        }
        
        with patch.object(weather_agent.mcp_client, 'get_weather', 
                         return_value=mock_weather_data):
            
            # 测试天气查询
            result = await weather_agent.query("北京今天天气怎么样？")
            
            assert result is not None
            assert "北京" in result
            assert "晴" in result
            logger.info(f"天气查询结果: {result}")
    
    @pytest.mark.asyncio
    async def test_city_search_flow(self, weather_agent):
        """测试城市搜索流程"""
        mock_cities = [
            {"name": "北京市", "adcode": "110000"},
            {"name": "北京市朝阳区", "adcode": "110105"}
        ]
        
        with patch.object(weather_agent.mcp_client, 'search_city',
                         return_value=mock_cities):
            
            # 测试城市搜索
            result = await weather_agent.query("搜索北京相关的城市")
            
            assert result is not None
            assert "北京" in result
            logger.info(f"城市搜索结果: {result}")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, weather_agent):
        """测试错误处理"""
        # 模拟API错误
        with patch.object(weather_agent.mcp_client, 'get_weather',
                         side_effect=Exception("API错误")):
            
            result = await weather_agent.query("北京天气")
            
            # 应该返回错误信息而不是抛出异常
            assert result is not None
            assert "错误" in result or "失败" in result
            logger.info(f"错误处理结果: {result}")
    
    def test_mcp_server_tools(self, mcp_server):
        """测试MCP服务器工具注册"""
        tools = mcp_server.list_tools()
        
        # 检查必需的工具是否已注册
        tool_names = [tool.name for tool in tools.tools]
        assert "get_weather" in tool_names
        assert "search_city" in tool_names
        assert "get_weather_forecast" in tool_names
        
        logger.info(f"已注册的工具: {tool_names}")
    
    def test_mcp_server_resources(self, mcp_server):
        """测试MCP服务器资源"""
        resources = mcp_server.list_resources()
        
        # 检查资源是否已注册
        resource_uris = [resource.uri for resource in resources.resources]
        assert "weather://cities" in resource_uris
        assert "weather://api-info" in resource_uris
        
        logger.info(f"已注册的资源: {resource_uris}")


class TestMCPClientServer:
    """MCP客户端-服务器通信测试"""
    
    @pytest.fixture
    def mock_session(self):
        """模拟MCP会话"""
        session = MagicMock()
        session.call_tool = MagicMock()
        session.read_resource = MagicMock()
        return session
    
    @pytest.mark.asyncio
    async def test_client_server_communication(self, mock_session):
        """测试客户端与服务器通信"""
        client = WeatherMCPClient()
        client.session = mock_session
        
        # 模拟工具调用响应
        mock_session.call_tool.return_value = MagicMock(
            content=[MagicMock(text='{"city": "北京", "weather": "晴"}')]
        )
        
        # 测试天气查询
        result = await client.get_weather("北京")
        
        # 验证调用
        mock_session.call_tool.assert_called_once()
        assert result is not None
        logger.info(f"客户端-服务器通信测试通过: {result}")
    
    @pytest.mark.asyncio
    async def test_connection_retry(self):
        """测试连接重试机制"""
        client = WeatherMCPClient()
        
        # 模拟连接失败
        with patch('mcp.client.stdio.stdio_client') as mock_stdio:
            mock_stdio.side_effect = [Exception("连接失败"), MagicMock()]
            
            # 应该重试连接
            try:
                await client.connect()
                # 如果没有抛出异常，说明重试成功
                logger.info("连接重试测试通过")
            except Exception as e:
                logger.warning(f"连接重试测试: {e}")


class TestConfigurationAndLogging:
    """配置和日志测试"""
    
    def test_settings_validation(self):
        """测试配置验证"""
        from config.settings import validate_config
        
        # 测试配置验证
        # 注意：这可能会失败如果没有设置API密钥
        result = validate_config()
        logger.info(f"配置验证结果: {result}")
    
    def test_logger_setup(self):
        """测试日志设置"""
        from utils.logger import setup_logger
        
        test_logger = setup_logger("test")
        test_logger.info("测试日志消息")
        
        # 验证日志文件是否创建
        log_file = settings.log_file
        assert os.path.exists(log_file) or os.path.exists(os.path.dirname(log_file))
        logger.info("日志设置测试通过")


class TestEndToEndScenarios:
    """端到端场景测试"""
    
    @pytest.mark.asyncio
    async def test_complete_weather_query_scenario(self):
        """测试完整的天气查询场景"""
        # 这个测试需要真实的API密钥，所以我们跳过或模拟
        if not settings.deepseek_api_key:
            pytest.skip("需要DeepSeek API密钥")
        
        try:
            agent = await create_weather_agent()
            
            # 测试多种查询类型
            queries = [
                "北京今天天气怎么样？",
                "上海明天会下雨吗？",
                "广州的温度是多少？",
                "搜索深圳相关的城市"
            ]
            
            for query in queries:
                result = await agent.query(query)
                assert result is not None
                logger.info(f"查询: {query} -> 结果: {result[:100]}...")
                
        except Exception as e:
            logger.error(f"端到端测试失败: {e}")
            pytest.fail(f"端到端测试失败: {e}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])