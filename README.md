# Description
利用和风天气官方api据制作的HomeAssistant天气预报组件，https://dev.heweather.com/docs/start/。

# 安装
放入 <config directory>/custom_components/heweather/ 目录

# 配置
**Example configuration.yaml:**
```yaml
weather:
  - platform: heweather
    name: 和风天气
    api_key: 1414c********96a9e458bdf680ffd8c
    region: 101210201
    scan_interval: 600
```

**Configuration variables:**

|  key   | description  |
|  ----  | ----  |
| name  | 名称，不设置，默认为“和风天气” |
| api_key  | 和风天气应用里面的“数据key” |
| region  | [城市编号](https://dev.heweather.com/docs/api/geo) |
| scan_interval  | 更新频率，单位秒，默认30秒一次，有点快 |

# 前台界面
前台界面有三种不同的选择
- lovelace的 [weather forcast](https://www.home-assistant.io/lovelace/weather-forecast/)
- 动态图标版 https://github.com/bramkragten/weather-card
- 博采众长版，能显示生活建议和预报图表（推荐） https://github.com/cnk700i/ha_modified_components/tree/master/hf_weather
    
### 程序说明（写给自己看的，请绕道）
天气插件获取的数据分为 *基础数据* 和 *进阶数据* 
* 基础数据，能满足lovelace界面中Weather Forecast Card的需求，具体数据项可以参考[官网](https://github.com/home-assistant/home-assistant/blob/dev/homeassistant/components/weather/__init__.py)
    1) temperature 当前温度
    2) temperature_unit 当前温度的单位（摄氏度和华氏度）
    3) pressure 大气压强
    4) humidity 空气湿度
    5) wind_speed 风速（公里/小时）
    6) wind_bearing 风向
    7) ozone 臭氧浓度
    8) attribution 版权归属信息
    9) visibility 能见度（公里）
    10) forecast 预报七天的数据（字典数组）
    11) precision 数据精度（已实现，默认0.1）
    12) state_attributes 相关属性值（已实现将基础数据全部放入属性）
    13) state 当前天气状态（已实现，返回condition）
    14) condition 当前天气状态
* 进阶数据，包括空气质量/小时预报和生活建议等数据，主要看得看数据源     
    1) suggestion 生活建议信息
    2) aqi 空气质量信息
    3) hourly_forecast 小时预报信息
    4) update_time 数据源更新时间
    5) 当前天气状态 中文
    6) 自定义更多天气信息属性
