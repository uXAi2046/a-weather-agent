"""
城市解析和匹配服务
"""

import re
from typing import List, Optional, Dict, Tuple
from difflib import SequenceMatcher
import jieba
from loguru import logger

from ..data.city_loader import CityDataLoader
from ..models.city import CityInfo, CitySearchResult


class CityParser:
    """城市解析器"""
    
    def __init__(self, city_loader: Optional[CityDataLoader] = None):
        """
        初始化城市解析器
        
        Args:
            city_loader: 城市数据加载器，如果为None则创建新实例
        """
        self.city_loader = city_loader or CityDataLoader()
        self.cities_cache: Dict[str, CityInfo] = {}
        self.name_to_cities: Dict[str, List[CityInfo]] = {}
        self._initialize_cache()
    
    def _initialize_cache(self):
        """初始化缓存"""
        try:
            self.cities_cache = self.city_loader.load_cities()
            
            # 构建名称到城市的映射
            self.name_to_cities.clear()
            for city in self.cities_cache.values():
                name = city.name
                if name not in self.name_to_cities:
                    self.name_to_cities[name] = []
                self.name_to_cities[name].append(city)
            
            logger.info(f"城市解析器初始化完成，加载了 {len(self.cities_cache)} 个城市")
            
        except Exception as e:
            logger.error(f"城市解析器初始化失败: {e}")
            raise
    
    def _normalize_city_name(self, name: str) -> str:
        """
        标准化城市名称
        
        Args:
            name: 原始城市名称
            
        Returns:
            标准化后的城市名称
        """
        if not name:
            return ""
        
        # 去除空格和特殊字符
        name = re.sub(r'\s+', '', name)
        
        # 常见后缀处理
        suffixes = ['市', '县', '区', '自治区', '自治州', '地区', '盟']
        for suffix in suffixes:
            if name.endswith(suffix):
                # 保留原名称，但也记录去掉后缀的版本
                break
        
        return name
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度分数 (0-1)
        """
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _extract_city_keywords(self, text: str) -> List[str]:
        """
        从文本中提取城市相关关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        # 使用jieba分词
        words = list(jieba.cut(text))
        
        # 过滤掉常见的非城市词汇
        stop_words = {
            '天气', '预报', '今天', '明天', '后天', '昨天', '现在', '当前',
            '怎么样', '如何', '查询', '看看', '的', '了', '吗', '呢', '啊',
            '温度', '气温', '下雨', '晴天', '阴天', '多云', '风', '湿度'
        }
        
        keywords = []
        for word in words:
            word = word.strip()
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
        
        return keywords
    
    def _match_by_exact_name(self, name: str) -> List[CityInfo]:
        """
        精确名称匹配
        
        Args:
            name: 城市名称
            
        Returns:
            匹配的城市列表
        """
        normalized_name = self._normalize_city_name(name)
        results = []
        
        # 直接匹配
        if normalized_name in self.name_to_cities:
            results.extend(self.name_to_cities[normalized_name])
        
        # 尝试添加常见后缀匹配
        if not results:
            suffixes = ['市', '县', '区']
            for suffix in suffixes:
                test_name = normalized_name + suffix
                if test_name in self.name_to_cities:
                    results.extend(self.name_to_cities[test_name])
        
        # 尝试去掉后缀匹配
        if not results:
            for suffix in ['市', '县', '区', '自治区', '自治州']:
                if normalized_name.endswith(suffix):
                    test_name = normalized_name[:-len(suffix)]
                    if test_name in self.name_to_cities:
                        results.extend(self.name_to_cities[test_name])
        
        return results
    
    def _match_by_fuzzy_name(self, name: str, threshold: float = 0.6, limit: int = 10) -> List[Tuple[CityInfo, float]]:
        """
        模糊名称匹配
        
        Args:
            name: 城市名称
            threshold: 相似度阈值
            limit: 返回结果数量限制
            
        Returns:
            匹配的城市列表，包含相似度分数
        """
        normalized_name = self._normalize_city_name(name)
        results = []
        
        for city_name, cities in self.name_to_cities.items():
            similarity = self._calculate_similarity(normalized_name, city_name)
            
            if similarity >= threshold:
                for city in cities:
                    results.append((city, similarity))
        
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def _match_by_adcode(self, adcode: str) -> Optional[CityInfo]:
        """
        根据adcode匹配城市
        
        Args:
            adcode: 行政区划代码
            
        Returns:
            匹配的城市信息
        """
        return self.cities_cache.get(adcode)
    
    def _is_adcode(self, text: str) -> bool:
        """
        判断文本是否为adcode
        
        Args:
            text: 输入文本
            
        Returns:
            是否为adcode
        """
        return text.isdigit() and len(text) == 6
    
    def parse_city_from_text(self, text: str, max_results: int = 10) -> CitySearchResult:
        """
        从文本中解析城市信息
        
        Args:
            text: 输入文本
            max_results: 最大返回结果数
            
        Returns:
            城市搜索结果
        """
        if not text:
            return CitySearchResult(search_query=text)
        
        text = text.strip()
        logger.debug(f"解析城市文本: {text}")
        
        # 检查是否为adcode
        if self._is_adcode(text):
            city = self._match_by_adcode(text)
            if city:
                return CitySearchResult(
                    matched_cities=[city],
                    exact_match=city,
                    search_query=text
                )
        
        # 提取关键词
        keywords = self._extract_city_keywords(text)
        logger.debug(f"提取的关键词: {keywords}")
        
        all_matches = []
        exact_match = None
        
        # 对每个关键词进行匹配
        for keyword in keywords:
            # 精确匹配
            exact_matches = self._match_by_exact_name(keyword)
            if exact_matches and not exact_match:
                exact_match = exact_matches[0]
            all_matches.extend(exact_matches)
            
            # 模糊匹配
            fuzzy_matches = self._match_by_fuzzy_name(keyword, threshold=0.6, limit=5)
            for city, score in fuzzy_matches:
                if city not in all_matches:
                    all_matches.append(city)
        
        # 如果没有关键词匹配，尝试整个文本
        if not all_matches:
            exact_matches = self._match_by_exact_name(text)
            if exact_matches:
                exact_match = exact_matches[0]
                all_matches.extend(exact_matches)
            else:
                fuzzy_matches = self._match_by_fuzzy_name(text, threshold=0.5, limit=max_results)
                all_matches.extend([city for city, score in fuzzy_matches])
        
        # 去重并限制结果数量
        unique_matches = []
        seen_adcodes = set()
        for city in all_matches:
            if city.adcode not in seen_adcodes:
                unique_matches.append(city)
                seen_adcodes.add(city.adcode)
                if len(unique_matches) >= max_results:
                    break
        
        # 分离精确匹配和模糊匹配
        fuzzy_matches = [city for city in unique_matches if city != exact_match]
        
        result = CitySearchResult(
            matched_cities=unique_matches,
            exact_match=exact_match,
            fuzzy_matches=fuzzy_matches,
            search_query=text
        )
        
        logger.info(f"城市解析结果: 查询='{text}', 精确匹配={exact_match.name if exact_match else None}, "
                   f"总匹配数={len(unique_matches)}")
        
        return result
    
    def get_city_by_name(self, name: str) -> Optional[CityInfo]:
        """
        根据名称获取城市（精确匹配）
        
        Args:
            name: 城市名称
            
        Returns:
            城市信息
        """
        matches = self._match_by_exact_name(name)
        return matches[0] if matches else None
    
    def get_city_by_adcode(self, adcode: str) -> Optional[CityInfo]:
        """
        根据adcode获取城市
        
        Args:
            adcode: 行政区划代码
            
        Returns:
            城市信息
        """
        return self._match_by_adcode(adcode)
    
    def search_cities(self, query: str, limit: int = 10) -> List[CityInfo]:
        """
        搜索城市
        
        Args:
            query: 搜索查询
            limit: 结果数量限制
            
        Returns:
            匹配的城市列表
        """
        result = self.parse_city_from_text(query, max_results=limit)
        return result.matched_cities
    
    def suggest_cities(self, partial_name: str, limit: int = 5) -> List[CityInfo]:
        """
        城市名称自动补全建议
        
        Args:
            partial_name: 部分城市名称
            limit: 建议数量限制
            
        Returns:
            建议的城市列表
        """
        if not partial_name:
            return []
        
        normalized_partial = self._normalize_city_name(partial_name)
        suggestions = []
        
        # 前缀匹配
        for city_name, cities in self.name_to_cities.items():
            if city_name.startswith(normalized_partial):
                suggestions.extend(cities)
                if len(suggestions) >= limit:
                    break
        
        # 如果前缀匹配不够，使用包含匹配
        if len(suggestions) < limit:
            for city_name, cities in self.name_to_cities.items():
                if normalized_partial in city_name and not any(c.adcode == cities[0].adcode for c in suggestions):
                    suggestions.extend(cities)
                    if len(suggestions) >= limit:
                        break
        
        return suggestions[:limit]