#!/usr/bin/env python3
"""
测试城市解析器
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from weather_mcp.services.city_parser import CityParser

def test_city_parser():
    """测试城市解析器功能"""
    print("=== 测试城市解析器 ===")
    
    # 初始化解析器
    parser = CityParser()
    
    # 测试用例
    test_cases = [
        "北京天气怎么样",
        "上海明天下雨吗",
        "深圳市",
        "广州",
        "杭州的温度",
        "成都今天多少度",
        "西安天气预报",
        "南京",
        "武汉市天气",
        "重庆",
        "110000",  # 北京adcode
        "310000",  # 上海adcode
        "北",      # 部分匹配
        "海南",    # 省份
        "不存在的城市"
    ]
    
    for query in test_cases:
        print(f"\n查询: '{query}'")
        result = parser.parse_city_from_text(query)
        
        if result.exact_match:
            print(f"  精确匹配: {result.exact_match.name} (adcode: {result.exact_match.adcode})")
        
        if result.fuzzy_matches:
            print(f"  模糊匹配: {[city.name for city in result.fuzzy_matches[:3]]}")
        
        if not result.matched_cities:
            print("  无匹配结果")
    
    # 测试自动补全
    print("\n=== 测试自动补全 ===")
    suggestions = parser.suggest_cities("北", limit=5)
    print(f"'北' 的建议: {[city.name for city in suggestions]}")
    
    suggestions = parser.suggest_cities("上", limit=5)
    print(f"'上' 的建议: {[city.name for city in suggestions]}")

if __name__ == "__main__":
    test_city_parser()