# Weather Agent 部署指南

## 概述

本文档详细说明了如何在不同环境中部署 Weather Agent 天气查询系统。

## 系统要求

### 最低要求
- Python 3.9+
- 内存: 512MB
- 磁盘空间: 100MB
- 网络: 需要访问外部API

### 推荐配置
- Python 3.11+
- 内存: 1GB+
- 磁盘空间: 500MB+
- CPU: 2核心+

## 环境准备

### 1. Python环境

```bash
# 检查Python版本
python --version

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 2. 依赖安装

```bash
# 安装依赖
pip install -r requirements.txt

# 验证安装
python -c "import langgraph, mcp, httpx; print('依赖安装成功')"
```

### 3. API密钥配置

#### 获取API密钥

1. **高德地图API密钥**
   - 访问: https://console.amap.com/
   - 注册账号并创建应用
   - 获取Web服务API密钥

2. **DeepSeek API密钥**
   - 访问: https://platform.deepseek.com/
   - 注册账号并获取API密钥

#### 配置环境变量

创建 `.env` 文件：

```env
# 必需配置
AMAP_API_KEY=your_amap_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 可选配置
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
LOG_LEVEL=INFO
CACHE_EXPIRE_MINUTES=5
```

## 部署方式

### 1. 本地开发部署

#### 快速启动

```bash
# 克隆项目
git clone <repository-url>
cd weather-agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入API密钥

# 运行设置向导
python main.py setup

# 启动交互式对话
python main.py chat
```

#### 验证部署

```bash
# 运行系统测试
python main.py test

# 单次查询测试
python main.py query "北京今天天气怎么样？"

# 查看配置
python main.py config
```

### 2. 生产环境部署

#### 使用systemd服务

创建服务文件 `/etc/systemd/system/weather-agent.service`：

```ini
[Unit]
Description=Weather Agent Service
After=network.target

[Service]
Type=simple
User=weather-agent
WorkingDirectory=/opt/weather-agent
Environment=PATH=/opt/weather-agent/venv/bin
ExecStart=/opt/weather-agent/venv/bin/python main.py chat
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start weather-agent

# 设置开机自启
sudo systemctl enable weather-agent

# 查看状态
sudo systemctl status weather-agent
```

#### 使用supervisor

安装supervisor：

```bash
sudo apt-get install supervisor
```

创建配置文件 `/etc/supervisor/conf.d/weather-agent.conf`：

```ini
[program:weather-agent]
command=/opt/weather-agent/venv/bin/python main.py chat
directory=/opt/weather-agent
user=weather-agent
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/weather-agent.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start weather-agent
```

### 3. Docker部署

#### 创建Dockerfile

```dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 weather-agent && \
    chown -R weather-agent:weather-agent /app

USER weather-agent

# 暴露端口（如果需要）
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# 启动命令
CMD ["python", "main.py", "chat"]
```

#### 构建和运行

```bash
# 构建镜像
docker build -t weather-agent:latest .

# 运行容器
docker run -d \
    --name weather-agent \
    --env-file .env \
    --restart unless-stopped \
    weather-agent:latest
```

#### 使用docker-compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  weather-agent:
    build: .
    container_name: weather-agent
    env_file: .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：添加Redis缓存
  redis:
    image: redis:7-alpine
    container_name: weather-agent-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

启动服务：

```bash
docker-compose up -d
```

### 4. 云平台部署

#### AWS EC2部署

1. **创建EC2实例**
   - 选择Ubuntu 20.04 LTS
   - 实例类型: t3.micro (免费套餐)
   - 配置安全组开放必要端口

2. **部署脚本**

```bash
#!/bin/bash
# 更新系统
sudo apt-get update && sudo apt-get upgrade -y

# 安装Python和pip
sudo apt-get install -y python3 python3-pip python3-venv git

# 克隆项目
git clone <repository-url> /opt/weather-agent
cd /opt/weather-agent

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
sudo cp .env.example .env
# 编辑 .env 文件

# 创建服务用户
sudo useradd -r -s /bin/false weather-agent
sudo chown -R weather-agent:weather-agent /opt/weather-agent

# 配置systemd服务
sudo cp deploy/weather-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable weather-agent
sudo systemctl start weather-agent
```

#### 阿里云ECS部署

类似AWS EC2，但需要注意：
- 使用阿里云的安全组配置
- 可以使用阿里云的负载均衡器
- 考虑使用阿里云的RDS作为数据存储

## 配置优化

### 1. 性能优化

#### 缓存配置

```env
# 增加缓存大小和时间
CACHE_MAX_SIZE=5000
CACHE_EXPIRE_MINUTES=10

# 启用Redis缓存（可选）
REDIS_URL=redis://localhost:6379/0
```

#### 并发配置

```env
# API请求配置
API_TIMEOUT=30
API_RETRY_TIMES=3
API_MAX_CONNECTIONS=100
```

### 2. 安全配置

#### 环境变量保护

```bash
# 设置文件权限
chmod 600 .env

# 使用密钥管理服务（生产环境）
# AWS: AWS Secrets Manager
# Azure: Azure Key Vault
# 阿里云: 密钥管理服务KMS
```

#### 网络安全

```bash
# 配置防火墙
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000  # 如果需要HTTP访问
```

### 3. 监控配置

#### 日志配置

```env
# 详细日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/weather_agent.log
LOG_ROTATION=10MB
LOG_RETENTION=7days
```

#### 监控脚本

创建 `scripts/health_check.py`：

```python
#!/usr/bin/env python3
"""健康检查脚本"""

import asyncio
import sys
from agent.weather_agent import create_weather_agent

async def health_check():
    try:
        agent = await create_weather_agent()
        result = await agent.query("系统状态检查")
        if result:
            print("系统正常")
            return 0
        else:
            print("系统异常")
            return 1
    except Exception as e:
        print(f"健康检查失败: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(health_check())
    sys.exit(exit_code)
```

## 故障排除

### 常见问题

#### 1. API密钥错误

**症状**: 提示API密钥无效
**解决方案**:
```bash
# 检查环境变量
python -c "import os; print('AMAP_API_KEY:', bool(os.getenv('AMAP_API_KEY')))"
python -c "import os; print('DEEPSEEK_API_KEY:', bool(os.getenv('DEEPSEEK_API_KEY')))"

# 重新配置
python main.py setup
```

#### 2. 网络连接问题

**症状**: 请求超时或连接失败
**解决方案**:
```bash
# 测试网络连接
curl -I https://api.deepseek.com
curl -I https://restapi.amap.com

# 检查防火墙设置
sudo ufw status
```

#### 3. 内存不足

**症状**: 进程被杀死或性能下降
**解决方案**:
```bash
# 检查内存使用
free -h
ps aux | grep python

# 优化配置
# 减少缓存大小
CACHE_MAX_SIZE=500
```

#### 4. 权限问题

**症状**: 无法写入日志或数据文件
**解决方案**:
```bash
# 检查文件权限
ls -la logs/
ls -la data/

# 修复权限
sudo chown -R weather-agent:weather-agent /opt/weather-agent
chmod 755 logs/ data/
```

### 调试工具

#### 启用调试模式

```env
LOG_LEVEL=DEBUG
```

#### 查看日志

```bash
# 实时查看日志
tail -f logs/weather_agent.log

# 搜索错误
grep -i error logs/weather_agent.log

# 查看系统日志
sudo journalctl -u weather-agent -f
```

## 维护

### 定期维护任务

#### 1. 日志清理

```bash
# 创建日志清理脚本
cat > scripts/cleanup_logs.sh << 'EOF'
#!/bin/bash
find logs/ -name "*.log" -mtime +7 -delete
find logs/ -name "*.log.gz" -mtime +30 -delete
EOF

chmod +x scripts/cleanup_logs.sh

# 添加到crontab
echo "0 2 * * * /opt/weather-agent/scripts/cleanup_logs.sh" | crontab -
```

#### 2. 缓存清理

```bash
# 清理过期缓存
python -c "
from weather_mcp.services.cache_service import CacheService
cache = CacheService()
cache.clear_expired()
print('缓存清理完成')
"
```

#### 3. 系统更新

```bash
# 更新依赖
pip install -r requirements.txt --upgrade

# 重启服务
sudo systemctl restart weather-agent
```

### 备份策略

#### 配置备份

```bash
# 备份配置文件
tar -czf backup/config_$(date +%Y%m%d).tar.gz .env config/

# 自动备份脚本
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/weather-agent"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/weather_agent_$DATE.tar.gz \
    .env config/ logs/ data/

# 保留最近7天的备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF
```

## 扩展部署

### 高可用部署

#### 负载均衡配置

使用Nginx作为负载均衡器：

```nginx
upstream weather_agent {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name weather-agent.example.com;
    
    location / {
        proxy_pass http://weather_agent;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 多实例部署

```bash
# 启动多个实例
for port in 8001 8002 8003; do
    PORT=$port python main.py chat &
done
```

### 微服务架构

将系统拆分为多个服务：

1. **API Gateway**: 统一入口
2. **Weather Service**: 天气数据服务
3. **Agent Service**: 智能对话服务
4. **Cache Service**: 缓存服务

## 总结

本部署指南涵盖了从开发环境到生产环境的完整部署流程。根据实际需求选择合适的部署方式，并注意安全性和可维护性。

如有问题，请参考故障排除章节或联系技术支持。