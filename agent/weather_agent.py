"""
LangGraph天气查询Agent
集成DeepSeek模型和MCP客户端，提供智能天气查询对话
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from .mcp_client import WeatherMCPClient, MCPClientError


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[List[BaseMessage], add_messages]
    user_input: str
    intent: Optional[str]
    mcp_tool: Optional[str]
    city: Optional[str]
    weather_type: Optional[str]
    extensions: Optional[str]
    weather_data: Optional[Dict[str, Any]]
    error: Optional[str]


class WeatherAgent:
    """天气查询智能Agent
    
    使用LangGraph框架和DeepSeek模型，提供自然语言天气查询服务
    """
    
    def __init__(self, 
                 deepseek_api_key: str,
                 mcp_server_command: List[str],
                 model_name: str = "deepseek-chat"):
        """初始化天气Agent
        
        Args:
            deepseek_api_key: DeepSeek API密钥
            mcp_server_command: MCP服务器启动命令
            model_name: 模型名称
        """
        self.deepseek_api_key = deepseek_api_key
        self.mcp_server_command = mcp_server_command
        self.model_name = model_name
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            api_key=deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=model_name,
            temperature=0.1
        )
        
        # 初始化MCP客户端
        self.mcp_client: Optional[WeatherMCPClient] = None
        
        # 构建对话图
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """构建LangGraph对话流程图"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("parse_and_extract", self._parse_and_extract)
        workflow.add_node("query_weather", self._query_weather)
        workflow.add_node("format_response", self._format_response)
        workflow.add_node("handle_error", self._handle_error)
        
        # 设置入口点
        workflow.set_entry_point("parse_and_extract")
        
        # 添加边
        workflow.add_conditional_edges(
            "parse_and_extract",
            self._should_continue_after_parse,
            {
                "query_weather": "query_weather",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "query_weather",
            self._should_continue_after_query,
            {
                "format_response": "format_response",
                "error": "handle_error"
            }
        )
        
        workflow.add_edge("format_response", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def _parse_and_extract(self, state: AgentState) -> AgentState:
        """统一解析用户意图和提取参数"""
        user_input = state["user_input"]
        
        system_prompt = """你是一个智能天气查询助手。请分析用户的输入，同时完成意图识别、参数提取和工具选择。

请以JSON格式返回结果：
{
    "intent": "意图类型",
    "mcp_tool": "MCP工具名称",
    "parameters": {
        "city": "城市名称",
        "weather_type": "天气类型",
        "extensions": "扩展参数"
    }
}

意图类型 (intent)：
- weather_query: 用户想查询天气信息
- city_search: 用户想搜索城市信息  
- help: 用户需要帮助
- other: 其他意图

MCP工具选择 (mcp_tool)：
- get_weather: 查询实时天气（当用户询问当前天气时）
- get_weather_forecast: 查询天气预报（当用户询问未来天气时）
- search_city: 搜索城市信息（当用户询问城市或城市名称不明确时）
- null: 不需要调用MCP工具

参数说明：
- city: 从用户输入中提取的城市名称，如果无法确定则为null
- weather_type: "live"(实时天气) 或 "forecast"(预报天气)，默认为"live"
- extensions: "base"(基础信息) 或 "all"(详细信息)，默认为"base"

示例：
用户："北京今天天气怎么样？" 
-> {"intent": "weather_query", "mcp_tool": "get_weather", "parameters": {"city": "北京", "weather_type": "live", "extensions": "base"}}

用户："上海明天会下雨吗？"
-> {"intent": "weather_query", "mcp_tool": "get_weather_forecast", "parameters": {"city": "上海", "weather_type": "forecast", "extensions": "base"}}"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户输入: {user_input}")
            ]
            
            # 记录模型输入
            logger.debug(f"[统一解析] 模型输入 - System Prompt: {system_prompt}")
            logger.debug(f"[统一解析] 模型输入 - User Message: 用户输入: {user_input}")
            logger.info(f"[统一解析] 开始调用DeepSeek模型进行统一解析: {user_input}")
            
            response = await self.llm.ainvoke(messages)
            result_text = response.content.strip()
            
            # 记录模型输出
            logger.debug(f"[统一解析] 模型原始输出: {response.content}")
            logger.info(f"[统一解析] 模型返回JSON: {result_text}")
            
            # 尝试解析JSON
            try:
                result = json.loads(result_text)
                
                # 提取各个字段
                state["intent"] = result.get("intent")
                state["mcp_tool"] = result.get("mcp_tool")
                
                parameters = result.get("parameters", {})
                state["city"] = parameters.get("city")
                state["weather_type"] = parameters.get("weather_type", "live")
                state["extensions"] = parameters.get("extensions", "base")
                
                logger.info(f"[统一解析] 解析成功 - 意图={state['intent']}, 工具={state['mcp_tool']}, 城市={state['city']}, 类型={state['weather_type']}")
                logger.debug(f"[统一解析] 完整解析结果: {result}")
                
                # 添加用户消息到对话历史
                state["messages"].append(HumanMessage(content=user_input))
                
            except json.JSONDecodeError:
                logger.error(f"[统一解析] JSON解析失败，无效格式: {result_text}")
                state["error"] = "无法解析用户请求"
                
        except Exception as e:
            logger.error(f"[统一解析] 模型调用失败: {e}")
            state["error"] = f"请求解析失败: {e}"
            
        return state
    
    async def _query_weather(self, state: AgentState) -> AgentState:
        """查询天气信息"""
        city = state["city"]
        weather_type = state["weather_type"]
        mcp_tool = state["mcp_tool"]
        extensions = state.get("extensions", "base")
        
        if not city:
            state["error"] = "请提供要查询的城市名称"
            return state
        
        if not mcp_tool:
            state["error"] = "未指定MCP工具"
            return state
        
        try:
            # 确保MCP客户端已连接
            if not self.mcp_client:
                self.mcp_client = WeatherMCPClient(self.mcp_server_command)
                await self.mcp_client.connect()
            
            # 根据mcp_tool调用相应的方法
            if mcp_tool == "get_weather":
                weather_result = await self.mcp_client.get_weather(city, weather_type)
            elif mcp_tool == "get_weather_forecast":
                # 预报天气使用forecast类型
                weather_result = await self.mcp_client.get_weather(city, "forecast")
            elif mcp_tool == "search_city":
                weather_result = await self.mcp_client.search_city(city)
            else:
                state["error"] = f"不支持的MCP工具: {mcp_tool}"
                return state
            
            # 解析结果
            if isinstance(weather_result, str):
                weather_data = json.loads(weather_result)
            else:
                weather_data = weather_result
            
            state["weather_data"] = weather_data
            logger.info(f"天气查询成功: {city}, 工具: {mcp_tool}")
            
        except MCPClientError as e:
            logger.error(f"MCP客户端错误: {e}")
            state["error"] = f"天气服务连接失败: {e}"
        except Exception as e:
            logger.error(f"天气查询失败: {e}")
            state["error"] = f"天气查询失败: {e}"
            
        return state
    
    async def _format_response(self, state: AgentState) -> AgentState:
        """格式化响应"""
        weather_data = state["weather_data"]
        city = state["city"]
        weather_type = state["weather_type"]
        
        if not weather_data:
            state["error"] = "没有获取到天气数据"
            return state
        
        system_prompt = """你是一个友好的天气播报员。请根据提供的天气数据，生成一个自然、友好的天气播报。

要求：
1. 使用自然的中文表达
2. 包含关键的天气信息
3. 语言要亲切友好
4. 如果是预报天气，要突出未来几天的趋势
5. 适当添加生活建议

请直接返回播报内容，不要添加额外的格式。"""
        
        try:
            user_message_content = f"城市: {city}\n天气类型: {weather_type}\n天气数据: {json.dumps(weather_data, ensure_ascii=False, indent=2)}"
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message_content)
            ]
            
            # 记录模型输入
            logger.debug(f"[响应格式化] 模型输入 - System Prompt: {system_prompt}")
            logger.debug(f"[响应格式化] 模型输入 - 天气数据: 城市={city}, 类型={weather_type}")
            logger.debug(f"[响应格式化] 模型输入 - 完整天气数据: {json.dumps(weather_data, ensure_ascii=False, indent=2)}")
            logger.info(f"[响应格式化] 开始调用DeepSeek模型生成天气播报: {city}")
            
            response = await self.llm.ainvoke(messages)
            formatted_response = response.content.strip()
            
            # 记录模型输出
            logger.debug(f"[响应格式化] 模型原始输出: {response.content}")
            logger.info(f"[响应格式化] 生成的天气播报长度: {len(formatted_response)} 字符")
            logger.debug(f"[响应格式化] 完整播报内容: {formatted_response}")
            
            state["messages"].append(AIMessage(content=formatted_response))
            logger.info(f"[响应格式化] 响应格式化完成，已添加到消息列表")
            
        except Exception as e:
            logger.error(f"[响应格式化] 模型调用失败: {e}")
            state["error"] = f"响应格式化失败: {e}"
            
        return state
    
    async def _handle_error(self, state: AgentState) -> AgentState:
        """处理错误"""
        error = state.get("error", "未知错误")
        user_input = state["user_input"]
        
        # 生成友好的错误响应
        error_responses = {
            "意图解析失败": "抱歉，我没有理解您的问题。您可以尝试问我关于天气的问题，比如'北京今天天气怎么样？'",
            "无法解析查询参数": "请告诉我您想查询哪个城市的天气，比如'上海的天气'或'广州明天天气预报'。",
            "请提供要查询的城市名称": "请告诉我您想查询哪个城市的天气。",
            "天气服务连接失败": "抱歉，天气服务暂时不可用，请稍后再试。",
            "天气查询失败": "抱歉，无法获取天气信息，请检查城市名称是否正确。"
        }
        
        # 查找匹配的错误响应
        response_text = error_responses.get(error, f"抱歉，出现了问题：{error}")
        
        # 如果是城市未找到的错误，尝试提供建议
        if "未找到城市" in error and isinstance(state.get("weather_data"), dict):
            suggestions = state["weather_data"].get("suggestions", [])
            if suggestions:
                suggestion_text = "、".join([city.get("name", "") for city in suggestions[:3]])
                response_text += f"\n\n您是否想查询：{suggestion_text}？"
        
        state["messages"].append(AIMessage(content=response_text))
        logger.info(f"错误处理完成: {error}")
        
        return state
    
    def _should_continue_after_parse(self, state: AgentState) -> str:
        """判断统一解析后的流程"""
        if state.get("error"):
            return "error"
        
        intent = state.get("intent", "")
        mcp_tool = state.get("mcp_tool")
        
        # 检查是否需要调用MCP工具
        if intent in ["weather_query", "city_search"] and mcp_tool:
            if state.get("city"):
                return "query_weather"
            else:
                state["error"] = "请提供要查询的城市名称"
                return "error"
        else:
            state["error"] = "暂不支持此类查询或无法确定查询参数"
            return "error"
    
    def _should_continue_after_query(self, state: AgentState) -> str:
        """判断天气查询后的流程"""
        if state.get("error"):
            return "error"
        
        if state.get("weather_data"):
            return "format_response"
        else:
            state["error"] = "没有获取到天气数据"
            return "error"
    
    async def chat(self, user_input: str) -> str:
        """处理用户输入并返回响应
        
        Args:
            user_input: 用户输入
            
        Returns:
            Agent响应
        """
        try:
            # 初始化状态
            initial_state = AgentState(
                messages=[],
                user_input=user_input,
                intent=None,
                city=None,
                weather_type=None,
                weather_data=None,
                error=None
            )
            
            # 运行对话图
            result = await self.graph.ainvoke(initial_state)
            
            # 提取最后的AI消息
            ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
            if ai_messages:
                return ai_messages[-1].content
            else:
                return "抱歉，我无法处理您的请求。"
                
        except Exception as e:
            logger.error(f"对话处理失败: {e}")
            return f"抱歉，处理您的请求时出现了错误：{e}"
    
    async def close(self):
        """关闭Agent，清理资源"""
        if self.mcp_client:
            await self.mcp_client.disconnect()
            self.mcp_client = None


# 便捷函数
async def create_weather_agent(deepseek_api_key: str, 
                              mcp_server_command: List[str]) -> WeatherAgent:
    """创建天气查询Agent
    
    Args:
        deepseek_api_key: DeepSeek API密钥
        mcp_server_command: MCP服务器启动命令
        
    Returns:
        天气查询Agent实例
    """
    return WeatherAgent(deepseek_api_key, mcp_server_command)


# 示例使用
async def main():
    """示例用法"""
    import os
    
    # 从环境变量获取API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("请设置DEEPSEEK_API_KEY环境变量")
        return
    
    # MCP服务器命令
    server_cmd = ["python", "-m", "weather_mcp.server"]
    
    try:
        # 创建Agent
        agent = await create_weather_agent(api_key, server_cmd)
        
        # 测试对话
        test_queries = [
            "北京今天天气怎么样？",
            "上海明天的天气预报",
            "广州这几天会下雨吗？",
            "深圳的温度是多少？"
        ]
        
        for query in test_queries:
            print(f"\n用户: {query}")
            response = await agent.chat(query)
            print(f"助手: {response}")
        
        # 关闭Agent
        await agent.close()
        
    except Exception as e:
        print(f"运行错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())