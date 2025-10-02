# app/services/cwa_transformer.py

from typing import Dict, Any, List

# CWA 數據中表示缺失或無效的常見值
INVALID_VALUES = ["-99", "-999", "T"]  # "T" (Trace) 也可能被視為無效值


def _safe_extract(data: Dict[str, Any], keys: List[str], default: str = "N/A") -> str:
    """
    通用輔助函式：安全地從巢狀字典中提取值，並處理 CWA 的無效值。

    例如：_safe_extract(record, ['WeatherElement', 'AirTemperature'])
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    # 將數值轉換為字串後，檢查是否為無效標記
    value_str = str(current).strip()
    if value_str in INVALID_VALUES or not value_str:
        return default

    return value_str


def transform_observation_data(
    json_data: Dict[str, Any], target_station_id: str
) -> str:
    """
    轉換 O-A0001-001 (氣象觀測站-全測站逐時氣象資料) JSON 為 AI 易讀格式。
    """
    stations = json_data.get("records", {}).get("Station", [])

    # 步驟 1: 尋找目標測站 (假設我們已經知道要找哪個測站)
    target_record = next(
        (s for s in stations if s.get("StationId") == target_station_id), None
    )

    if not target_record:
        return f"🚨 O-A0001-001: 未找到測站 ID {target_station_id} 的觀測資料。"

    # 步驟 2: 安全提取關鍵氣象要素
    name = _safe_extract(target_record, ["StationName"])
    time = _safe_extract(target_record, ["ObsTime", "DateTime"])

    weather_elem = target_record.get("WeatherElement", {})

    temp = _safe_extract(weather_elem, ["AirTemperature"])
    humidity = _safe_extract(weather_elem, ["RelativeHumidity"])
    wind_speed = _safe_extract(weather_elem, ["WindSpeed"])
    weather = _safe_extract(weather_elem, ["Weather"])

    # 提取當日溫度的極值 (用於判斷溫差風險)
    daily_high = _safe_extract(
        weather_elem, ["DailyExtreme", "DailyHigh", "TemperatureInfo", "AirTemperature"]
    )
    daily_low = _safe_extract(
        weather_elem, ["DailyExtreme", "DailyLow", "TemperatureInfo", "AirTemperature"]
    )

    # 步驟 3: 格式化為 AI 易讀的摘要

    return f"""
📢 即時氣象觀測 (O-A0001-001) - 測站: {name} ({target_station_id})
---
[觀測時間]: {time}
[天氣現象]: {weather}
[氣溫/濕度]: {temp} °C, 相對濕度 {humidity}%
[風速]: {wind_speed} m/s (請注意風速 > 5 m/s 即有感)
[今日溫差參考]: 最高 {daily_high} °C / 最低 {daily_low} °C
---
"""


def transform_rainfall_data(json_data: Dict[str, Any], target_station_id: str) -> str:
    """
    轉換 O-A0002-001 (雨量觀測站-雨量資料) JSON 為 AI 易讀格式。
    """
    stations = json_data.get("records", {}).get("Station", [])

    # 步驟 1: 尋找目標測站
    target_record = next(
        (s for s in stations if s.get("StationId") == target_station_id), None
    )

    if not target_record:
        return f"🚨 O-A0002-001: 未找到測站 ID {target_station_id} 的雨量資料。"

    # 步驟 2: 安全提取累積雨量要素
    name = _safe_extract(target_record, ["StationName"])
    time = _safe_extract(target_record, ["ObsTime", "DateTime"])

    rainfall_elem = target_record.get("RainfallElement", {})

    # 提取短期和累積雨量
    precip_now = _safe_extract(rainfall_elem, ["Now", "Precipitation"])
    precip_1hr = _safe_extract(rainfall_elem, ["Past1hr", "Precipitation"])
    precip_3hr = _safe_extract(rainfall_elem, ["Past3hr", "Precipitation"])
    precip_24hr = _safe_extract(rainfall_elem, ["Past24hr", "Precipitation"])

    # 步驟 3: 格式化為 AI 易讀的摘要
    # AI 判讀重點：24 小時累積雨量是判斷路徑泥濘和危險的重要指標
    return f"""
💧 即時雨量觀測 (O-A0002-001) - 測站: {name} ({target_station_id})
---
[觀測時間]: {time}
[當前雨勢]: {precip_now} mm
[過去 1 小時累積]: {precip_1hr} mm (短期路徑濕滑指標)
[過去 3 小時累積]: {precip_3hr} mm
[過去 24 小時累積]: {precip_24hr} mm (🚨 路徑泥濘/積水風險指標)
---
"""
