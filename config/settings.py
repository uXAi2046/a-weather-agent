"""
配置管理模块
使用pydantic-settings管理应用配置
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # API配置
    amap_api_key: str = Field(
        default="",
        description="高德地图API密钥"
    )
    
    deepseek_api_key: Optional[str] = Field(
        default=None,
        description="DeepSeek API密钥"
    )
    
    # 模型配置
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek模型名称"
    )
    
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API基础URL"
    )
    
    # 缓存配置
    cache_expire_minutes: int = Field(
        default=5,
        description="缓存过期时间（分钟）"
    )
    
    cache_max_size: int = Field(
        default=1000,
        description="缓存最大条目数"
    )
    
    # API请求配置
    api_timeout: int = Field(
        default=30,
        description="API请求超时时间（秒）"
    )
    
    api_retry_times: int = Field(
        default=3,
        description="API请求重试次数"
    )
    
    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    log_file: str = Field(
        default="logs/weather_agent.log",
        description="日志文件路径"
    )
    
    # MCP配置
    mcp_server_timeout: int = Field(
        default=30,
        description="MCP服务器连接超时时间（秒）"
    )
    
    mcp_max_retries: int = Field(
        default=3,
        description="MCP连接最大重试次数"
    )
    
    # 城市匹配配置
    city_match_threshold: float = Field(
        default=0.6,
        description="城市模糊匹配阈值"
    )
    
    city_search_limit: int = Field(
        default=10,
        description="城市搜索结果限制"
    )
    
    class Config:
        """配置类设置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例"""
    return settings


# 配置验证函数
def validate_config() -> bool:
    """验证配置是否完整"""
    errors = []
    
    # 检查必需的API密钥
    if not settings.amap_api_key:
        errors.append("缺少高德地图API密钥 (AMAP_API_KEY)")
    
    if not settings.deepseek_api_key:
        errors.append("缺少DeepSeek API密钥 (DEEPSEEK_API_KEY)")
    
    # 检查数值配置
    if settings.cache_expire_minutes <= 0:
        errors.append("缓存过期时间必须大于0")
    
    if settings.api_timeout <= 0:
        errors.append("API超时时间必须大于0")
    
    if settings.city_match_threshold < 0 or settings.city_match_threshold > 1:
        errors.append("城市匹配阈值必须在0-1之间")
    
    if errors:
        print("配置验证失败:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def print_config():
    """打印当前配置"""
    print("当前配置:")
    print(f"  高德地图API密钥: {'已设置' if settings.amap_api_key else '未设置'}")
    print(f"  DeepSeek API密钥: {'已设置' if settings.deepseek_api_key else '未设置'}")
    print(f"  DeepSeek模型: {settings.deepseek_model}")
    print(f"  缓存过期时间: {settings.cache_expire_minutes}分钟")
    print(f"  API超时时间: {settings.api_timeout}秒")
    print(f"  日志级别: {settings.log_level}")
    print(f"  城市匹配阈值: {settings.city_match_threshold}")


if __name__ == "__main__":
    print_config()
    print(f"\n配置验证: {'通过' if validate_config() else '失败'}")