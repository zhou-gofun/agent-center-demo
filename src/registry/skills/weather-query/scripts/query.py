#!/usr/bin/env python3
"""
Weather Query Script

Query real-time weather for Chinese cities using AMap (高德地图) API.
"""
import argparse
import json
import sys
import os
import re
from typing import Dict, Any
from datetime import datetime
import urllib.parse

# AMap API Configuration
AMAP_KEY = os.getenv("AMAP_KEY", "")
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"


def query_weather(city: str, extensions: str = "base") -> Dict[str, Any]:
    """
    Query real-time weather for a given city using AMap API.

    Args:
        city: City name (e.g., "成都", "北京", "上海") or adcode
        extensions: "base" for current weather, "all" for forecast

    Returns:
        Weather data dictionary
    """
    if not city:
        return {
            "success": False,
            "error": "Missing city parameter"
        }

    try:
        import urllib.request
        import urllib.error

        # Build request URL with proper URL encoding
        params = {
            "key": AMAP_KEY,
            "city": city,
            "extensions": extensions
        }
        url = f"{AMAP_WEATHER_URL}?{urllib.parse.urlencode(params, encoding='utf-8')}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }

        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))

        # Check API response status
        if result.get("status") != "1":
            error_msg = result.get("info", "Unknown error")
            return {
                "success": False,
                "error": f"API Error: {error_msg}",
                "city": city
            }

        # Parse weather data
        weather_data = parse_amap_response(result, city)

        return {
            "success": True,
            "city": city,
            "data": weather_data
        }

    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP Error {e.code}: {e.reason}",
            "city": city
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Connection Error: {e.reason}",
            "city": city
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "city": city
        }


def parse_amap_response(response: Dict, city: str) -> Dict[str, Any]:
    """
    Parse AMap API response and extract relevant fields.

    Args:
        response: Raw API response
        city: City name

    Returns:
        Parsed weather data
    """
    data = {}

    # Handle live weather (base)
    if "lives" in response and response["lives"]:
        live = response["lives"][0]
        data["type"] = "current"
        data["province"] = live.get("province", "")
        data["city"] = live.get("city", "")
        data["adcode"] = live.get("adcode", "")
        data["weather"] = live.get("weather", "")
        data["temperature"] = live.get("temperature", "")
        data["wind_direction"] = live.get("winddirection", "")
        data["wind_power"] = live.get("windpower", "")
        data["humidity"] = live.get("humidity", "")
        data["report_time"] = live.get("reporttime", "")

    # Handle forecast (all)
    elif "forecasts" in response and response["forecasts"]:
        forecast = response["forecasts"][0]
        data["type"] = "forecast"
        data["city"] = forecast.get("city", "")
        data["adcode"] = forecast.get("adcode", "")
        data["province"] = forecast.get("province", "")
        data["report_time"] = forecast.get("reporttime", "")
        data["casts"] = forecast.get("casts", [])

    return data


def format_weather_output(result: Dict[str, Any]) -> str:
    """
    Format weather query result for display.

    Args:
        result: Query result from query_weather()

    Returns:
        Formatted string for display
    """
    if not result.get("success"):
        return f"❌ 查询失败: {result.get('error', 'Unknown error')}"

    data = result.get("data", {})

    if data.get("type") == "current":
        return format_current_weather(data)
    elif data.get("type") == "forecast":
        return format_forecast_weather(data)
    else:
        return "❓ 未知天气数据类型"


def format_current_weather(data: Dict) -> str:
    """Format current/live weather data."""
    lines = [
        f"📍 {data.get('city', '')} 实时天气",
        "━━━━━━━━━━━━━━━━━━"
    ]

    # Weather
    if "weather" in data:
        lines.append(f"☁️  天气：{data['weather']}")

    # Temperature
    if "temperature" in data:
        temp = data["temperature"]
        lines.append(f"🌡️  温度：{temp}°C")

    # Humidity
    if "humidity" in data:
        humidity = data["humidity"]
        lines.append(f"💧 湿度：{humidity}%")

    # Wind
    wind_dir = data.get("wind_direction", "")
    wind_power = data.get("wind_power", "")

    if wind_dir or wind_power:
        wind_parts = []
        if wind_dir:
            wind_parts.append(f"{wind_dir}风")
        if wind_power:
            wind_parts.append(f"{wind_power}级")

        if wind_parts:
            lines.append(f"🌬️  风向风力：{' '.join(wind_parts)}")

    # Update time
    if "report_time" in data:
        time_str = data["report_time"]
        lines.append(f"⏱️  更新时间：{time_str}")

    # Add suggestion
    lines.append("")
    lines.append(generate_suggestion(data))

    return "\n".join(lines)


def format_forecast_weather(data: Dict) -> str:
    """Format forecast weather data."""
    lines = [
        f"📍 {data.get('city', '')} 天气预报",
        "━━━━━━━━━━━━━━━━━━"
    ]

    casts = data.get("casts", [])
    for cast in casts[:4]:  # Show up to 4 days
        date = cast.get("date", "")
        week = cast.get("week", "")
        day_weather = cast.get("dayweather", "")
        night_weather = cast.get("nightweather", "")
        day_temp = cast.get("daytemp", "")
        night_temp = cast.get("nighttemp", "")
        day_wind = cast.get("daywind", "")
        day_power = cast.get("daypower", "")

        lines.append(f"📅 {date} ({week})")
        lines.append(f"   白天：{day_weather} {day_temp}°C {day_wind}风 {day_power}级")
        lines.append(f"   晚上：{night_weather} {night_temp}°C")
        lines.append("")

    return "\n".join(lines)


def generate_suggestion(data: Dict) -> str:
    """
    Generate a brief suggestion based on weather conditions.
    """
    weather = str(data.get("weather", "")).lower()
    temp_str = str(data.get("temperature", "20"))

    # Extract temperature number
    temp_match = re.search(r'-?\d+', temp_str)
    temp = int(temp_match.group()) if temp_match else 20

    suggestions = []

    # Temperature based suggestions
    if temp < 5:
        suggestions.append("天气寒冷，注意保暖，建议穿羽绒服或棉衣。")
    elif temp < 15:
        suggestions.append("天气较凉，建议穿外套或毛衣。")
    elif temp < 25:
        suggestions.append("天气舒适，适合穿着长袖或薄外套。")
    elif temp < 32:
        suggestions.append("天气温暖，适合穿着短袖或薄衫。")
    else:
        suggestions.append("天气炎热，注意防暑降温，多饮水。")

    # Weather condition based suggestions
    if "雨" in weather or "rain" in weather.lower():
        suggestions.append("有降雨，出门请带伞，注意路面湿滑。")
    elif "雪" in weather or "snow" in weather.lower():
        suggestions.append("有降雪，注意保暖，路面可能结冰请小心。")
    elif "雾" in weather or "霾" in weather or "fog" in weather.lower():
        suggestions.append("能见度较低，出行请注意安全，驾车慢行。")

    return suggestions[0] if suggestions else "天气不错，祝您有美好的一天！"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Query real-time weather for Chinese cities")
    parser.add_argument("--city", type=str, help="City name (e.g., 成都, 北京, 上海)")
    parser.add_argument("--forecast", action="store_true", help="Get forecast instead of current weather")

    args = parser.parse_args()

    # Try to read JSON input from stdin first (for skill execution)
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        try:
            input_data = json.loads(stdin_data)
            # Check if it's the UniversalScriptExecutor format
            if "__entrypoint__" in input_data:
                city_value = input_data["__input__"].get("city", "")
                if city_value:
                    args.city = city_value
                if input_data["__input__"].get("forecast"):
                    args.forecast = True
            else:
                # Direct JSON input
                city_value = input_data.get("city", "")
                if city_value:
                    args.city = city_value
                if input_data.get("forecast"):
                    args.forecast = True
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            if not args.city:
                args.city = stdin_data

    if not args.city:
        parser.error("--city is required or provide via stdin")

    extensions = "all" if args.forecast else "base"
    result = query_weather(args.city, extensions)

    # 添加格式化输出到 result 字段，供 LLM 直接使用
    if result.get("success"):
        formatted_output = format_weather_output(result)
        result["result"] = formatted_output

    # Output JSON to stdout for programmatic use
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Output formatted weather to stderr for human readability
    if result.get("success"):
        print("\n--- Weather Report ---", file=sys.stderr)
        print(result.get("result", ""), file=sys.stderr)


if __name__ == "__main__":
    main()
