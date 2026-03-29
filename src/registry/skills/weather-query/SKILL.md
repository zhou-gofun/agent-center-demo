---
name: weather-query
description: 查询实时天气，获取指定城市的当前天气信息
allowed-tools: []
context: inline
execution:
  type: script
  handler: scripts/query.py
  entrypoint: query_weather
  timeout: 30
---

# Weather Query

查询中国任意城市的实时天气信息，包括温度、湿度、风向风力、天气现象等。使用高德地图 API。

## When to Use

Use this skill when:
- User asks for current weather of a city
- User asks "天气如何" or "天气怎么样"
- User wants to know temperature, humidity, wind conditions
- User mentions a city name with weather-related questions

## Input Requirements

Required:
- `city`: 城市名称，如"成都"、"北京"、"上海" 或城市 adcode

Optional:
- `forecast`: 设为 true 获取天气预报而非实时天气

## API

使用高德地图天气 API:
```
GET https://restapi.amap.com/v3/weather/weatherInfo?key=xxx&city=<城市名>&extensions=base
```

## Output Format

### 实时天气 (base)
```
📍 <城市名> 实时天气
━━━━━━━━━━━━━━━━━━
☁️  天气：晴
🌡️  温度：22°C
💧 湿度：45%
🌬️  风向风力：东南风 3级
⏱️  更新时间：2026-03-29 17:00
```

### 天气预报 (all)
```
📍 <城市名> 天气预报
━━━━━━━━━━━━━━━━━━
📅 2026-03-29 (星期日)
   白天：晴 25°C 东南风 3级
   晚上：晴 15°C
...
```

## Using the Script

```bash
# 实时天气
python scripts/query.py --city "成都"

# 天气预报
python scripts/query.py --city "成都" --forecast
```

Or as a module:

```python
from registry.skills.weather_query.scripts.query import query_weather

# 实时天气
result = query_weather(city="成都", extensions="base")

# 天气预报
result = query_weather(city="成都", extensions="all")
```

## Response Fields

- `success`: 是否成功
- `city`: 城市名称
- `data.type`: "current" (实时) 或 "forecast" (预报)
- `data.weather`: 天气现象
- `data.temperature`: 温度 (°C)
- `data.humidity`: 湿度 (%)
- `data.wind_direction`: 风向
- `data.wind_power`: 风力等级
- `data.report_time`: 更新时间
- `data.casts`: 预报数据列表 (仅预报模式)
