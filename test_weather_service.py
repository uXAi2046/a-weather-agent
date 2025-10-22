#!/usr/bin/env python3
"""
测试天气服务
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('.'))

# 加载环境变量
load_dotenv()

from weather_mcp.services.weather_service import WeatherService, WeatherServiceSync

async def test_weather_service():
    """测试天气服务功能"""
    print("=== 测试天气服务 ===")
    
    # 获取API密钥
    api_key = os.getenv('AMAP_API_KEY')
    if not api_key:
        print("错误: 未找到AMAP_API_KEY环境变量")
        return
    
    # 初始化服务
    service = WeatherService(api_key)
    
    # 测试用例
    test_queries = [
        "北京天气",
        "上海市",
        "深圳",
        "广州明天天气",
        "杭州的温度",
        "110000",  # 北京adcode
        "不存在的城市"
    ]
    
    for query in test_queries:
        print(f"\n--- 测试查询: '{query}' ---")
        
        try:
            # 测试实时天气
            print("获取实时天气...")
            live_result = await service.get_live_weather(query)
            
            city_info = live_result['city']
            weather_info = live_result['weather']
            query_info = live_result['query_info']
            
            print(f"城市: {city_info['name']} (adcode: {city_info['adcode']})")
            print(f"精确匹配: {query_info['exact_match']}")
            
            if weather_info:
                print(f"天气: {weather_info.weather}")
                print(f"温度: {weather_info.temperature}°C")
                print(f"湿度: {weather_info.humidity}%")
                print(f"风向: {weather_info.winddirection}")
                print(f"风力: {weather_info.windpower}")
            
            if query_info['alternative_cities']:
                print(f"其他匹配城市: {[city['name'] for city in query_info['alternative_cities']]}")
            
            # 测试天气预报
            print("\n获取天气预报...")
            forecast_result = await service.get_forecast_weather(query)
            
            forecast_info = forecast_result['forecast']
            if forecast_info and forecast_info['casts']:
                print(f"预报天数: {len(forecast_info['casts'])}")
                for i, cast in enumerate(forecast_info['casts'][:3]):  # 显示前3天
                    print(f"  第{i+1}天 ({cast['date']}): {cast['dayweather']} / {cast['nightweather']}, "
                          f"{cast['daytemp']}°C / {cast['nighttemp']}°C")
            
        except Exception as e:
            print(f"错误: {e}")
    
    # 测试城市搜索
    print(f"\n--- 测试城市搜索 ---")
    search_results = service.search_cities("北京", limit=5)
    print(f"搜索'北京'的结果: {[city['name'] for city in search_results]}")
    
    # 测试城市建议
    suggestions = service.get_city_suggestions("上", limit=5)
    print(f"'上'的建议: {[city['name'] for city in suggestions]}")
    
    # 测试缓存统计
    cache_stats = service.get_cache_stats()
    print(f"\n缓存统计: {cache_stats}")

def test_sync_service():
    """测试同步服务"""
    print("\n=== 测试同步天气服务 ===")
    
    api_key = os.getenv('AMAP_API_KEY')
    if not api_key:
        print("错误: 未找到AMAP_API_KEY环境变量")
        return
    
    # 创建同步服务
    async_service = WeatherService(api_key)
    sync_service = WeatherServiceSync(async_service)
    
    try:
        # 测试同步调用
        result = sync_service.get_live_weather("北京")
        city_info = result['city']
        weather_info = result['weather']
        
        print(f"同步调用结果:")
        print(f"城市: {city_info['name']}")
        if weather_info:
            print(f"天气: {weather_info.weather}")
            print(f"温度: {weather_info.temperature}°C")
        
    except Exception as e:
        print(f"同步调用错误: {e}")

if __name__ == "__main__":
    # 测试异步服务
    asyncio.run(test_weather_service())
    
    # 测试同步服务
    test_sync_service()