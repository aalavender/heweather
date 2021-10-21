#from datetime import datetime, timedelta

#https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/weather/__init__.py
from homeassistant.components.weather import (
    WeatherEntity, ATTR_FORECAST_CONDITION, ATTR_FORECAST_PRECIPITATION, 
    ATTR_FORECAST_TEMP, ATTR_FORECAST_TEMP_LOW, ATTR_FORECAST_TIME, ATTR_FORECAST_WIND_BEARING, ATTR_FORECAST_WIND_SPEED)

#https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/const.py
from homeassistant.const import (TEMP_CELSIUS, TEMP_FAHRENHEIT, CONF_API_KEY, CONF_REGION, CONF_NAME)

import requests
import json
import logging
import asyncio

VERSION = '0.1.0'
DOMAIN = 'heweather'

'''超过ha自定weather属性的额外数据，需要额外注册'''
ATTR_AQI = "aqi"
ATTR_HOURLY_FORECAST = "hourly_forecast"
ATTR_SUGGESTION = "suggestion"
ATTR_UPDATE_TIME = "update_time"
ATTR_CONDITION_CN = "condition_cn"
ATTR_CLOUD_PERCENT = "cloud_percent"  #云量，百分比
ATTR_TEMPERATURE_FEELS  = "temperature_feels" # 体感温度
ATTR_WIND_DIR = "wind_dir" #风向
ATTR_WIND_SCALE = "wind_sacle" #风力

#在7天的预报信息中添加如下信息
ATTR_FORECAST_SUN_RISE = "sun_rise"  #日出时间
ATTR_FORECAST_SUN_SET = "sun_set"    #日落时间
ATTR_FORECAST_MOON_RISE = "moon_rise"    #月升时间
ATTR_FORECAST_MOON_SET = "moon_set"      #月落时间    
ATTR_FORECAST_MOON_PHASE = "moon_phase"  #月相

ATTR_FORECAST_PRECIPITATION_PROBABILITY = "precipitation_probability"
# mapping state, why? because
# https://developers.home-assistant.io/docs/core/entity/weather#recommended-values-for-state-and-condition
# https://dev.heweather.com/docs/refer/condition
# 和风天气状态多，ha状态少，需要多对一
CONDITION_MAP = {
    '100': 'sunny', #晴  Sunny/Clear
    '101': 'partlycloudy',  #多云
    '102': 'partlycloudy',  #少云
    '103': 'partlycloudy',  #晴间多云
    '104': 'cloudy',    #阴
    
    '150': 'clear-night', #夜晚晴
    '153': 'partlycloudy', #夜晚多云
    '154': 'cloudy', #夜晚阴

    '300': 'rainy',  #阵雨
    '301': 'rainy',  #强阵雨
    '302': 'lightning-rainy',  # 雷阵雨
    '303': 'lightning-rainy',  # 强雷阵雨
    '304': 'hail',  # 雷阵雨伴有冰雹
    '305': 'rainy',  # 小雨
    '306': 'rainy',  # 中雨
    '307': 'rainy',     # 大雨
    '308': 'hail',     #极端降雨
    '309': 'rainy',    #毛毛雨/细雨
    '310': 'pouring',  #暴雨
    '311': 'pouring',  #大暴雨
    '312': 'pouring',  #特大暴雨
    '313': 'hail',  #冻雨
    '314': 'rainy',  # 小到中雨
    '315': 'rainy',  # 中到大雨
    '316': 'pouring',  #大到暴雨
    '317': 'pouring',  #暴雨到大暴雨
    '318': 'pouring',  #大暴雨到特大暴雨
    '399': 'rainy',  #雨
    '350': 'rainy',  #阵雨
    '351': 'rainy',  #强阵雨

    '400': 'snowy',  #小雪
    '401': 'snowy',  #中雪
    '402': 'snowy',  #大雪
    '403': 'hail',  #暴雪
    '404': 'snowy-rainy',  #雨夹雪
    '405': 'snowy-rainy',  #雨雪天气
    '406': 'snowy-rainy',  #阵雨夹雪
    '407': 'snowy',  # 阵雪
    '408': 'snowy',  # 小到中雪
    '409': 'snowy',  # 中到大雪
    '410': 'snowy',  # 大到暴雪
    '499': 'snowy',  # 雪
    '456': 'snowy-rainy',  #阵雨夹雪
    '457': 'snowy',  # 阵雪

    '500': 'fog',  # 薄雾
    '501': 'fog',  # 雾
    '502': 'fog',  # 霾
    '503': 'fog',  # 扬沙
    '504': 'fog',  # 浮尘
    '507': 'hail',  # 沙尘暴
    '508': 'hail',  # 强沙尘暴
    '509': 'fog',  # 浓雾
    '510': 'fog',  # 强浓雾
    '511': 'fog',  # 中度霾
    '512': 'fog',  # 重度霾
    '513': 'hail',  # 严重霾
    '514': 'fog',  # 大雾
    '515': 'hail',  # 特强浓雾

    '900': 'exceptional',  # 热
    '901': 'exceptional',  # 冷
    '999': 'exceptional',  # 未知
}

_LOGGER = logging.getLogger(__name__)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    _LOGGER.info("async_setup_platform sensor HeWeather")
    async_add_devices([HeWeather(api_key=config.get(CONF_API_KEY),
                            region=config.get(CONF_REGION, '101210201'),  #默认为湖州
                            name=config.get(CONF_NAME, '和风天气'))], True)

#基类 https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/weather/__init__.py
class HeWeather(WeatherEntity):
    """Representation of a weather condition."""

    def __init__(self, api_key: str, region: str, name: str):
        self._api_key = api_key
        self._region = region
        self._name = name
        self._msg = "初始化"
        self._data_source_update = None # 数据源更新时间
        self._now_warning = None        # 存储灾害预警
        self._now_weather_data = None   # 存储实况天气数据
        self._now_air_data = None       # 存储实况空气质量数据
        self._now_life_data = None      # 存储实况生活指数数据
        self._daily_forecast_data = None    # 存储天气预报数据（未来7天）
        self._hourly_forecast_data = None   # 存储天气预报数据（未来24小时）

    @property
    def name(self):
        return self._name

    @property
    def condition(self):
        """Return the weather condition."""
        if self._now_weather_data:
            return CONDITION_MAP[self._now_weather_data["icon"]]
        else:
            return self._msg
    @property
    def cloud_percent(self):
        """实况云量，百分比数值"""
        if self._now_weather_data:
            return float(self._now_weather_data['cloud'])
        else:
            return self._msg

    @property
    def condition_cn(self):
        """Return the weather condition by txt"""
        if self._now_weather_data:
            return self._now_weather_data["text"]
        else:
            return self._msg
    @property
    def temperature(self):
        if self._now_weather_data:
            return float(self._now_weather_data['temp'])
        else:
            return self._msg

    @property
    def temperature_feels(self):
        """体感温度"""
        if self._now_weather_data:
            return float(self._now_weather_data['feelsLike'])
        else:
            return self._msg

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def pressure(self):
        """大气压强"""
        if self._now_weather_data:
            return float(self._now_weather_data['pressure'])
        else:
            return self._msg

    @property
    def humidity(self):
        if self._now_weather_data:
            return float(self._now_weather_data['humidity'])
        else:
            return self._msg

    @property
    def wind_speed(self):
        """风速"""
        if self._now_weather_data:
            return float(self._now_weather_data["windSpeed"])
        else:
            return self._msg

    @property
    def wind_bearing(self):
        """风的角度"""
        if self._now_weather_data:
            return float(self._now_weather_data["wind360"])
        else:
            return self._msg

    @property
    def wind_dir(self):
        """风向"""
        if self._now_weather_data:
            return self._now_weather_data["windDir"]
        else:
            return self._msg
    @property
    def wind_sacle(self):
        """风力"""
        if self._now_weather_data:
            return float(self._now_weather_data["windScale"])
        else:
            return self._msg


    @property
    def ozone(self):
        """臭氧浓度"""
        if self._now_air_data:
            return self._now_air_data['o3']
        else:
            return self._msg

    @property
    def attribution(self):
        """Return the attribution."""
        return 'https://dev.heweather.com/'

    @property
    def visibility(self):
        """能见度"""
        if self._now_weather_data:
            return self._now_weather_data['vis']
        else:
            return self._msg

    @property
    def state_attributes(self):
        '''注册自定义的属性'''
        data = super(HeWeather, self).state_attributes
        data[ATTR_SUGGESTION] = self.suggestion
        data[ATTR_AQI] = self.aqi
        data[ATTR_HOURLY_FORECAST] = self.hourly_forecast
        data[ATTR_UPDATE_TIME] = self.update_time
        data[ATTR_CONDITION_CN] = self.condition_cn
        data[ATTR_CLOUD_PERCENT] = self.cloud_percent
        data[ATTR_TEMPERATURE_FEELS] = self.temperature_feels
        data[ATTR_WIND_DIR] = self.wind_dir
        data[ATTR_WIND_SCALE] = self.wind_sacle
        return data

    @property
    def forecast(self):
        """天为单位的预报"""
        forecast_data = []
        if self._daily_forecast_data:
            for i in range(len(self._daily_forecast_data)):
                data_dict = {
                    ATTR_FORECAST_TIME: self._daily_forecast_data[i]["fxDate"],
                    ATTR_FORECAST_CONDITION: CONDITION_MAP[self._daily_forecast_data[i]["iconDay"]],
                    ATTR_FORECAST_PRECIPITATION: float(self._daily_forecast_data[i]["precip"]),
                    ATTR_FORECAST_TEMP: float(self._daily_forecast_data[i]["tempMax"]),
                    ATTR_FORECAST_TEMP_LOW: float(self._daily_forecast_data[i]["tempMin"]),
                    ATTR_FORECAST_WIND_BEARING: float(self._daily_forecast_data[i]["wind360Day"]),
                    ATTR_FORECAST_WIND_SPEED: float(self._daily_forecast_data[i]["windSpeedDay"]),
                    ATTR_FORECAST_SUN_RISE: self._daily_forecast_data[i]["sunrise"],
                    ATTR_FORECAST_SUN_SET: self._daily_forecast_data[i]["sunset"],
                    ATTR_FORECAST_MOON_RISE: self._daily_forecast_data[i]["moonrise"],
                    ATTR_FORECAST_MOON_SET: self._daily_forecast_data[i]["moonset"],
                    ATTR_FORECAST_MOON_PHASE: self._daily_forecast_data[i]["moonPhase"]
                }
                forecast_data.append(data_dict)

        return forecast_data

    @property
    def suggestion(self):
        if self._now_life_data:
            return self._now_life_data
#            return [{'title': k, 'title_cn': SUGGESTION_MAP.get(k,k), 'brf': v.get('brf'),
#                                    'txt': v.get('txt') } for k, v in self._now_life_data.items()]
        else:
            return self._msg

    @property
    def aqi(self):
        """AQI（国标）"""
        if self._now_air_data:
            return self._now_air_data
        else:
            return self._msg

    @property
    def update_time(self):
        """数据源更新时间."""
        if self._data_source_update:
            return self._data_source_update
        else:
            return self._msg
    @property
    def hourly_forecast(self):
        """小时为单位的预报"""
        forecast_data = []
        if self._hourly_forecast_data:
            for i in range(len(self._hourly_forecast_data)):
                data_dict = {
                    ATTR_FORECAST_TIME: self._hourly_forecast_data[i]["fxTime"],
                    ATTR_FORECAST_CONDITION: CONDITION_MAP[self._hourly_forecast_data[i]["icon"]],
                    ATTR_FORECAST_PRECIPITATION_PROBABILITY: float(self._hourly_forecast_data[i]["pop"]),  # 降水概率
                    ATTR_FORECAST_TEMP: float(self._hourly_forecast_data[i]["temp"])
                }
                forecast_data.append(data_dict)

        return forecast_data

    def update(self):
        _LOGGER.info("HeWeather updating from  https://devapi.qweather.net/v7")
        #实况天气，字典
        self._msg = requests.get("https://devapi.qweather.net/v7/weather/now?location={0}&key={1}".format(self._region,self._api_key)).content
        self._now_weather_data  = json.loads(self._msg)["now"]
        self._data_source_update  = json.loads(self._msg)["updateTime"]
        #空气质量实况，字典
        self._msg = requests.get("https://devapi.qweather.net/v7/air/now?location={0}&key={1}".format(self._region,self._api_key)).content
        self._now_air_data  = json.loads(self._msg)["now"]       
        #灾害预警，字典数组
        self._msg = requests.get("https://devapi.qweather.net/v7/warning/now?location={0}&key={1}".format(self._region,self._api_key)).content
        self._now_warning  = json.loads(self._msg)["warning"] 
        #生活指数，字典数组
        self._msg = requests.get("https://devapi.qweather.net/v7/indices/1d?location={0}&key={1}&type=0".format(self._region,self._api_key)).content
        self._now_life_data  = json.loads(self._msg)["daily"] 
        #未来7天预报，包括当天，字典数组
        self._msg = requests.get("https://devapi.qweather.net/v7/weather/7d?location={0}&key={1}".format(self._region,self._api_key)).content
        self._daily_forecast_data  = json.loads(self._msg)["daily"] 
        #未来24小时，下一个整点开始，逐小时预报，字典数据
        self._msg = requests.get("https://devapi.qweather.net/v7/weather/24h?location={0}&key={1}".format(self._region,self._api_key)).content
        self._hourly_forecast_data  = json.loads(self._msg)["hourly"]         