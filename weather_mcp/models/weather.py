"""
天气数据模型定义
"""

from typing import Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator


class LiveWeather(BaseModel):
    """实时天气数据模型"""
    
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")
    adcode: str = Field(..., description="区域编码")
    weather: str = Field(..., description="天气现象")
    temperature: str = Field(..., description="实时气温，单位：摄氏度")
    winddirection: str = Field(..., description="风向")
    windpower: str = Field(..., description="风力等级")
    humidity: str = Field(..., description="空气湿度")
    reporttime: str = Field(..., description="数据发布的时间")
    
    @validator('temperature', pre=True)
    def validate_temperature(cls, v):
        """验证温度格式"""
        # 保持原始值，不进行格式化
        return v
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            str: lambda v: v.strip() if v else v
        }


class ForecastWeatherCast(BaseModel):
    """天气预报单日数据模型"""
    
    date: str = Field(..., description="日期")
    week: str = Field(..., description="星期几")
    dayweather: str = Field(..., description="白天天气现象")
    nightweather: str = Field(..., description="夜晚天气现象")
    daytemp: str = Field(..., description="白天温度")
    nighttemp: str = Field(..., description="夜晚温度")
    daywind: str = Field(..., description="白天风向")
    nightwind: str = Field(..., description="夜晚风向")
    daypower: str = Field(..., description="白天风力")
    nightpower: str = Field(..., description="夜晚风力")
    
    @validator('daytemp', 'nighttemp', pre=True)
    def validate_temperature(cls, v):
        """验证温度格式"""
        # 保持原始值，不进行格式化
        return v


class ForecastWeather(BaseModel):
    """天气预报数据模型"""
    
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")
    adcode: str = Field(..., description="区域编码")
    reporttime: str = Field(..., description="预报发布时间")
    casts: List[ForecastWeatherCast] = Field(default_factory=list, description="预报数据")
    
    class Config:
        """Pydantic配置"""
        json_encoders = {
            str: lambda v: v.strip() if v else v
        }


class WeatherResponse(BaseModel):
    """高德天气API响应模型"""
    
    status: str = Field(..., description="返回状态")
    count: Optional[str] = Field(None, description="返回结果总数目")
    info: str = Field(..., description="返回的状态信息")
    infocode: str = Field(..., description="返回状态说明")
    lives: Optional[List[LiveWeather]] = Field(None, description="实况天气数据信息")
    forecasts: Optional[List[ForecastWeather]] = Field(None, description="预报天气信息")
    
    @property
    def is_success(self) -> bool:
        """是否请求成功"""
        return self.status == "1" and self.infocode == "10000"
    
    @property
    def has_live_data(self) -> bool:
        """是否有实况数据"""
        return self.lives is not None and len(self.lives) > 0
    
    @property
    def has_forecast_data(self) -> bool:
        """是否有预报数据"""
        return self.forecasts is not None and len(self.forecasts) > 0
    
    @property
    def first_live(self) -> Optional[LiveWeather]:
        """获取第一个实况数据"""
        if self.has_live_data:
            return self.lives[0]
        return None
    
    @property
    def first_forecast(self) -> Optional[ForecastWeather]:
        """获取第一个预报数据"""
        if self.has_forecast_data:
            return self.forecasts[0]
        return None


class WeatherQuery(BaseModel):
    """天气查询请求模型"""
    
    city: str = Field(..., description="城市名称或adcode")
    extensions: str = Field(default="base", description="返回结果控制，base返回实况天气，all返回预报天气")
    output: str = Field(default="JSON", description="返回格式")
    
    @validator('extensions')
    def validate_extensions(cls, v):
        """验证extensions参数"""
        if v not in ["base", "all"]:
            raise ValueError("extensions must be 'base' or 'all'")
        return v
    
    @validator('output')
    def validate_output(cls, v):
        """验证output参数"""
        if v.upper() not in ["JSON", "XML"]:
            raise ValueError("output must be 'JSON' or 'XML'")
        return v.upper()


class WeatherError(Exception):
    """天气API错误"""
    
    def __init__(self, message: str, status: str = None, infocode: str = None):
        self.message = message
        self.status = status
        self.infocode = infocode
        super().__init__(self.message)