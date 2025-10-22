# Weather Agent API 文档

## 概述

Weather Agent 是一个基于 MCP (Model Context Protocol) 的智能天气查询系统，集成了 DeepSeek 大语言模型，提供自然语言天气查询服务。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Weather Agent  │    │   MCP Client    │
│                 │◄──►│   (LangGraph)   │◄──►│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  DeepSeek API   │    │   MCP Server    │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Weather Service │
                                               │   (AMap API)    │
                                               └─────────────────┘
```

## 核心组件

### 1. Weather Agent (agent/weather_agent.py)

基于 LangGraph 的智能对话代理，负责：
- 自然语言意图理解
- 参数提取和验证
- 天气查询协调
- 响应格式化

#### 主要方法

```python
class WeatherAgent:
    async def query(self, user_input: str) -> str:
        """处理用户查询"""
        
    async def parse_intent(self, state: AgentState) -> AgentState:
        """解析用户意图"""
        
    async def extract_parameters(self, state: AgentState) -> AgentState:
        """提取查询参数"""
        
    async def query_weather(self, state: AgentState) -> AgentState:
        """查询天气信息"""
        
    async def format_response(self, state: AgentState) -> AgentState:
        """格式化响应"""
```

### 2. MCP Client (agent/mcp_client.py)

MCP 协议客户端，负责与 Weather MCP Server 通信：

```python
class WeatherMCPClient:
    async def connect(self) -> bool:
        """连接到MCP服务器"""
        
    async def disconnect(self):
        """断开连接"""
        
    async def get_weather(self, city: str) -> dict:
        """获取天气信息"""
        
    async def search_city(self, query: str) -> list:
        """搜索城市"""
        
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用MCP工具"""
```

### 3. MCP Server (weather_mcp/server.py)

MCP 协议服务器，提供天气查询工具和资源：

#### 注册的工具

| 工具名称 | 描述 | 参数 | 返回值 |
|---------|------|------|--------|
| `get_weather` | 获取实时天气 | `city: str` | 天气信息对象 |
| `search_city` | 搜索城市 | `query: str` | 城市列表 |
| `get_weather_forecast` | 获取天气预报 | `city: str, days: int` | 预报信息 |

#### 注册的资源

| 资源URI | 描述 | 内容类型 |
|---------|------|----------|
| `weather://cities` | 城市数据 | JSON |
| `weather://api-info` | API信息 | JSON |

### 4. Weather Service (weather_mcp/services/weather_service.py)

天气数据服务，封装高德地图API：

```python
class WeatherService:
    async def get_weather(self, city: str) -> dict:
        """获取天气信息"""
        
    async def get_forecast(self, city: str, days: int = 3) -> dict:
        """获取天气预报"""
        
    def _format_weather_data(self, data: dict) -> dict:
        """格式化天气数据"""
```

## API 接口

### 1. 命令行接口

```bash
# 交互式对话
python main.py chat

# 单次查询
python main.py query "北京今天天气怎么样？"

# 显示配置
python main.py config

# 系统测试
python main.py test

# 设置向导
python main.py setup
```

### 2. 编程接口

#### 创建 Weather Agent

```python
from agent.weather_agent import create_weather_agent

# 创建代理实例
agent = await create_weather_agent()

# 查询天气
result = await agent.query("北京今天天气怎么样？")
print(result)
```

#### 直接使用 MCP Client

```python
from agent.mcp_client import WeatherMCPClient

# 创建客户端
client = WeatherMCPClient()

# 连接服务器
await client.connect()

# 查询天气
weather_data = await client.get_weather("北京")

# 搜索城市
cities = await client.search_city("北京")

# 断开连接
await client.disconnect()
```

## 数据格式

### 天气信息格式

```json
{
    "city": "北京市",
    "adcode": "110000",
    "weather": "晴",
    "temperature": "25",
    "temperature_float": 25.0,
    "humidity": "60",
    "wind_direction": "东",
    "wind_power": "2",
    "report_time": "2024-01-15 14:30:00",
    "formatted_info": "北京市：晴，25°C，湿度60%，东风2级"
}
```

### 城市信息格式

```json
{
    "name": "北京市",
    "adcode": "110000",
    "center": "116.407526,39.90403",
    "level": "province",
    "districts": []
}
```

### 错误响应格式

```json
{
    "error": true,
    "message": "错误描述",
    "code": "ERROR_CODE",
    "details": {}
}
```

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `AMAP_API_KEY` | 高德地图API密钥 | - | 是 |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | - | 是 |
| `DEEPSEEK_MODEL` | DeepSeek模型名称 | `deepseek-chat` | 否 |
| `LOG_LEVEL` | 日志级别 | `INFO` | 否 |
| `CACHE_EXPIRE_MINUTES` | 缓存过期时间 | `5` | 否 |

### 配置文件 (.env)

```env
# API配置
AMAP_API_KEY=your_amap_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# 模型配置
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 缓存配置
CACHE_EXPIRE_MINUTES=5
CACHE_MAX_SIZE=1000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/weather_agent.log
```

## 错误处理

### 常见错误类型

1. **API密钥错误**
   - 错误码: `INVALID_API_KEY`
   - 解决方案: 检查并更新API密钥

2. **网络连接错误**
   - 错误码: `NETWORK_ERROR`
   - 解决方案: 检查网络连接，重试请求

3. **城市不存在**
   - 错误码: `CITY_NOT_FOUND`
   - 解决方案: 使用城市搜索功能找到正确的城市名称

4. **MCP连接错误**
   - 错误码: `MCP_CONNECTION_ERROR`
   - 解决方案: 重启MCP服务器，检查连接配置

### 错误处理策略

- **自动重试**: API请求失败时自动重试最多3次
- **降级处理**: 当某个服务不可用时，提供基础功能
- **用户友好**: 将技术错误转换为用户可理解的消息
- **日志记录**: 详细记录错误信息用于调试

## 性能优化

### 缓存策略

- **内存缓存**: 使用LRU缓存存储天气数据
- **缓存时间**: 天气数据缓存5分钟
- **缓存大小**: 最多缓存1000条记录

### 并发处理

- **异步IO**: 所有网络请求使用异步处理
- **连接池**: 复用HTTP连接减少开销
- **超时控制**: 设置合理的请求超时时间

## 扩展开发

### 添加新的天气数据源

1. 实现 `WeatherProvider` 接口
2. 在 `WeatherService` 中注册新的提供者
3. 更新配置文件添加相关参数

### 添加新的MCP工具

1. 在 `WeatherMCPServer` 中定义新工具
2. 实现工具处理逻辑
3. 更新客户端添加对应方法

### 自定义Agent行为

1. 修改 `WeatherAgent` 的状态图
2. 添加新的节点和边
3. 实现相应的处理函数

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行集成测试
pytest tests/test_integration.py

# 运行特定测试
pytest tests/test_integration.py::TestWeatherAgentIntegration::test_weather_query_flow
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 部署

### 本地部署

1. 安装依赖: `pip install -r requirements.txt`
2. 配置环境变量
3. 运行: `python main.py chat`

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py", "chat"]
```

## 许可证

MIT License - 详见 LICENSE 文件