# 天气查询Agent

基于LangGraph和MCP协议的智能天气查询系统。

## 功能特性

- 🌤️ 支持实时天气和天气预报查询
- 🏙️ 智能城市名称匹配（支持模糊匹配）
- 🗺️ 覆盖中国大陆县级以上城市
- 🤖 基于DeepSeek模型的自然语言交互
- 📡 MCP协议标准化接口
- ⚡ 高性能缓存机制

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd weather-agent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# DEEPSEEK_API_KEY=your_deepseek_api_key
# AMAP_API_KEY=your_amap_api_key
```

#### API密钥获取方式

1. **DeepSeek API密钥**
   - 访问 [DeepSeek平台](https://platform.deepseek.com/)
   - 注册账号并登录
   - 在API管理页面创建新的API密钥
   - 将密钥填入 `.env` 文件的 `DEEPSEEK_API_KEY` 字段

2. **高德地图API密钥**
   - 访问 [高德开放平台](https://console.amap.com/)
   - 注册开发者账号并登录
   - 创建应用并申请Web服务API密钥
   - 将密钥填入 `.env` 文件的 `AMAP_API_KEY` 字段

⚠️ **安全提醒**: 请勿将包含真实API密钥的 `.env` 文件提交到版本控制系统中。

### 3. 运行

```bash
# 启动MCP服务器
python -m weather_mcp.server

# 或直接使用命令行工具
python main.py "北京今天天气怎么样？"
```

## 项目结构

```
weather-agent/
├── weather_mcp/          # MCP服务器核心模块
│   ├── data/            # 城市数据和加载器
│   ├── models/          # 数据模型定义
│   ├── clients/         # API客户端
│   └── services/        # 业务服务
├── agent/               # LangGraph Agent
├── config/              # 配置管理
├── utils/               # 工具函数
├── tests/               # 测试用例
├── docs/                # 文档和数据
└── main.py              # 主程序入口
```

## API文档

详见 [docs/amap_weather_api.md](docs/amap_weather_api.md)

## 开发指南

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black .
isort .
```

## 许可证

MIT License