"""
城市数据模型定义
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class CityInfo(BaseModel):
    """城市信息模型"""
    
    adcode: str = Field(..., description="行政区划代码")
    citycode: str = Field(..., description="城市代码")
    name: str = Field(..., description="城市名称")
    center: Optional[str] = Field(None, description="城市中心坐标")
    level: Optional[str] = Field(None, description="行政级别")
    parent: Optional[str] = Field(None, description="上级行政区划代码")
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            str: lambda v: v.strip() if v else v
        }


class CitySearchResult(BaseModel):
    """城市搜索结果模型"""
    
    matched_cities: List[CityInfo] = Field(default_factory=list, description="匹配的城市列表")
    exact_match: Optional[CityInfo] = Field(None, description="精确匹配的城市")
    fuzzy_matches: List[CityInfo] = Field(default_factory=list, description="模糊匹配的城市列表")
    search_query: str = Field(..., description="搜索查询")
    
    @property
    def has_results(self) -> bool:
        """是否有搜索结果"""
        return len(self.matched_cities) > 0
    
    @property
    def best_match(self) -> Optional[CityInfo]:
        """最佳匹配结果"""
        if self.exact_match:
            return self.exact_match
        elif self.fuzzy_matches:
            return self.fuzzy_matches[0]
        elif self.matched_cities:
            return self.matched_cities[0]
        return None


class ProvinceInfo(BaseModel):
    """省份信息模型"""
    
    adcode: str = Field(..., description="省份行政区划代码")
    name: str = Field(..., description="省份名称")
    cities: List[CityInfo] = Field(default_factory=list, description="下属城市列表")
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            str: lambda v: v.strip() if v else v
        }