"""
城市数据加载器
"""

import os
import json
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
from loguru import logger

from ..models.city import CityInfo, ProvinceInfo


class CityDataLoader:
    """城市数据加载器"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化城市数据加载器
        
        Args:
            data_dir: 数据目录路径，默认为当前模块的data目录
        """
        if data_dir is None:
            data_dir = Path(__file__).parent
        self.data_dir = Path(data_dir)
        self.cities_cache: Dict[str, CityInfo] = {}
        self.provinces_cache: Dict[str, ProvinceInfo] = {}
        self._loaded = False
    
    def load_from_excel(self, excel_path: str) -> Dict[str, CityInfo]:
        """
        从Excel文件加载城市数据
        
        Args:
            excel_path: Excel文件路径
            
        Returns:
            城市数据字典，key为adcode
        """
        try:
            logger.info(f"正在从Excel文件加载城市数据: {excel_path}")
            
            # 读取Excel文件
            df = pd.read_excel(excel_path)
            
            # 数据清洗和转换
            cities = {}
            for _, row in df.iterrows():
                try:
                    # 处理citycode中的\N值
                    citycode = str(row.get('citycode', '')).strip()
                    if citycode == '\\N' or citycode == 'nan':
                        citycode = ''
                    
                    city = CityInfo(
                        adcode=str(row.get('adcode', '')).strip(),
                        citycode=citycode,
                        name=str(row.get('中文名', '')).strip(),  # 使用正确的列名
                        center=str(row.get('center', '')).strip() if pd.notna(row.get('center')) else None,
                        level=str(row.get('level', '')).strip() if pd.notna(row.get('level')) else None,
                        parent=str(row.get('parent', '')).strip() if pd.notna(row.get('parent')) else None
                    )
                    
                    if city.adcode and city.name:
                        cities[city.adcode] = city
                        
                except Exception as e:
                    logger.warning(f"解析城市数据行时出错: {e}, 行数据: {row.to_dict()}")
                    continue
            
            logger.info(f"成功加载 {len(cities)} 个城市数据")
            return cities
            
        except Exception as e:
            logger.error(f"从Excel文件加载城市数据失败: {e}")
            raise
    
    def save_to_json(self, cities: Dict[str, CityInfo], json_path: str):
        """
        将城市数据保存为JSON文件
        
        Args:
            cities: 城市数据字典
            json_path: JSON文件保存路径
        """
        try:
            logger.info(f"正在保存城市数据到JSON文件: {json_path}")
            
            # 确保目录存在
            Path(json_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为可序列化的格式
            cities_data = {
                adcode: city.model_dump() for adcode, city in cities.items()
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cities_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存 {len(cities)} 个城市数据到JSON文件")
            
        except Exception as e:
            logger.error(f"保存城市数据到JSON文件失败: {e}")
            raise
    
    def load_from_json(self, json_path: str) -> Dict[str, CityInfo]:
        """
        从JSON文件加载城市数据
        
        Args:
            json_path: JSON文件路径
            
        Returns:
            城市数据字典，key为adcode
        """
        try:
            logger.info(f"正在从JSON文件加载城市数据: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                cities_data = json.load(f)
            
            cities = {}
            for adcode, city_data in cities_data.items():
                try:
                    city = CityInfo(**city_data)
                    cities[adcode] = city
                except Exception as e:
                    logger.warning(f"解析城市数据时出错: {e}, 数据: {city_data}")
                    continue
            
            logger.info(f"成功从JSON文件加载 {len(cities)} 个城市数据")
            return cities
            
        except Exception as e:
            logger.error(f"从JSON文件加载城市数据失败: {e}")
            raise
    
    def load_cities(self, force_reload: bool = False) -> Dict[str, CityInfo]:
        """
        加载城市数据（优先从JSON加载，如果不存在则从Excel加载并保存为JSON）
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            城市数据字典，key为adcode
        """
        if self._loaded and not force_reload and self.cities_cache:
            return self.cities_cache
        
        json_path = self.data_dir / "cities.json"
        excel_path = self.data_dir.parent.parent / "docs" / "AMap_adcode_citycode.xlsx"
        
        # 优先从JSON加载
        if json_path.exists() and not force_reload:
            try:
                self.cities_cache = self.load_from_json(str(json_path))
                self._loaded = True
                return self.cities_cache
            except Exception as e:
                logger.warning(f"从JSON加载失败，尝试从Excel加载: {e}")
        
        # 从Excel加载
        if excel_path.exists():
            try:
                self.cities_cache = self.load_from_excel(str(excel_path))
                # 保存为JSON以便下次快速加载
                self.save_to_json(self.cities_cache, str(json_path))
                self._loaded = True
                return self.cities_cache
            except Exception as e:
                logger.error(f"从Excel加载城市数据失败: {e}")
                raise
        else:
            raise FileNotFoundError(f"城市数据文件不存在: {excel_path}")
    
    def get_provinces(self) -> Dict[str, ProvinceInfo]:
        """
        获取省份数据（基于城市数据构建）
        
        Returns:
            省份数据字典，key为省份adcode
        """
        if self.provinces_cache:
            return self.provinces_cache
        
        cities = self.load_cities()
        provinces = {}
        
        for city in cities.values():
            # 省级行政区的adcode通常是前2位+0000或前4位+00
            province_code = None
            if len(city.adcode) >= 6:
                if city.adcode.endswith('0000'):
                    # 这是省级行政区
                    province_code = city.adcode
                else:
                    # 这是市级或县级，提取省级代码
                    province_code = city.adcode[:2] + '0000'
            
            if province_code and province_code not in provinces:
                # 查找省级行政区名称
                province_city = cities.get(province_code)
                if province_city:
                    provinces[province_code] = ProvinceInfo(
                        adcode=province_code,
                        name=province_city.name,
                        cities=[]
                    )
        
        # 将城市分配到对应省份
        for city in cities.values():
            if not city.adcode.endswith('0000'):  # 排除省级行政区本身
                province_code = city.adcode[:2] + '0000'
                if province_code in provinces:
                    provinces[province_code].cities.append(city)
        
        self.provinces_cache = provinces
        return provinces
    
    def get_city_by_adcode(self, adcode: str) -> Optional[CityInfo]:
        """
        根据adcode获取城市信息
        
        Args:
            adcode: 行政区划代码
            
        Returns:
            城市信息，如果不存在返回None
        """
        cities = self.load_cities()
        return cities.get(adcode)
    
    def get_city_by_name(self, name: str) -> Optional[CityInfo]:
        """
        根据名称获取城市信息（精确匹配）
        
        Args:
            name: 城市名称
            
        Returns:
            城市信息，如果不存在返回None
        """
        cities = self.load_cities()
        for city in cities.values():
            if city.name == name:
                return city
        return None
    
    def search_cities_by_name(self, name: str, limit: int = 10) -> List[CityInfo]:
        """
        根据名称搜索城市（模糊匹配）
        
        Args:
            name: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            匹配的城市列表
        """
        cities = self.load_cities()
        results = []
        
        name = name.strip()
        if not name:
            return results
        
        # 精确匹配优先
        for city in cities.values():
            if city.name == name:
                results.insert(0, city)
                if len(results) >= limit:
                    break
        
        # 包含匹配
        if len(results) < limit:
            for city in cities.values():
                if name in city.name and city not in results:
                    results.append(city)
                    if len(results) >= limit:
                        break
        
        # 被包含匹配
        if len(results) < limit:
            for city in cities.values():
                if city.name in name and city not in results:
                    results.append(city)
                    if len(results) >= limit:
                        break
        
        return results[:limit]