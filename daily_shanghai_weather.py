#!/usr/bin/env python3
"""Send Shanghai workday weather email with today's 18:00 rain status and temperature."""

from __future__ import annotations

import argparse
import json
import os
import smtplib
import ssl
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo


SHANGHAI_LATITUDE = 31.2304
SHANGHAI_LONGITUDE = 121.4737
SHANGHAI_TIMEZONE = "Asia/Shanghai"
WTTR_LOCATION = "Shanghai"

WEATHER_CODE_TEXT = {
    0: "晴",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴",
    45: "雾",
    48: "霜雾",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴强冰雹",
}

WTTR_WEATHER_CODE_TEXT = {
    "113": "晴",
    "116": "局部多云",
    "119": "阴",
    "122": "阴",
    "143": "雾",
    "176": "小雨",
    "179": "雨夹雪",
    "182": "冻雨",
    "185": "冻雨",
    "200": "雷暴",
    "227": "小雪",
    "230": "暴雪",
    "248": "雾",
    "260": "雾",
    "263": "小毛毛雨",
    "266": "小雨",
    "281": "冻毛毛雨",
    "284": "冻毛毛雨",
    "293": "小雨",
    "296": "小雨",
    "299": "中雨",
    "302": "中雨",
    "305": "大雨",
    "308": "大雨",
    "311": "冻雨",
    "314": "冻雨",
    "317": "雨夹雪",
    "320": "雨夹雪",
    "323": "小阵雪",
    "326": "小阵雪",
    "329": "中雪",
    "332": "中雪",
    "335": "大雪",
    "338": "大雪",
    "350": "冰粒",
    "353": "小阵雨",
    "356": "中等阵雨",
    "359": "强阵雨",
    "362": "小阵雪",
    "365": "强阵雪",
    "368": "小阵雪",
    "371": "强阵雪",
    "374": "冰粒",
    "377": "冰粒",
    "386": "雷暴伴小雨",
    "389": "雷暴",
    "392": "雷暴伴雪",
    "395": "雷暴伴强阵雪",
}

RAIN_LEVEL_BY_CODE = {
    "51": "小雨",
    "53": "小雨",
    "55": "中雨",
    "56": "小雨",
    "57": "中雨",
    "61": "小雨",
    "63": "中雨",
    "65": "大雨",
    "66": "中雨",
    "67": "大雨",
    "80": "小雨",
    "81": "中雨",
    "82": "大雨",
    "95": "暴雨",
    "96": "暴雨",
    "99": "暴雨",
    "176": "小雨",
    "179": "小雨",
    "182": "中雨",
    "185": "中雨",
    "263": "小雨",
    "266": "小雨",
    "281": "小雨",
    "284": "中雨",
    "293": "小雨",
    "296": "小雨",
    "299": "中雨",
    "302": "中雨",
    "305": "大雨",
    "308": "大雨",
    "311": "中雨",
    "314": "大雨",
    "317": "小雨",
    "320": "中雨",
    "353": "小雨",
    "356": "中雨",
    "359": "大雨",
    "386": "暴雨",
    "389": "暴雨",
    "392": "暴雨",
    "395": "暴雨",
}


@dataclass(frozen=True)
class Forecast:
    forecast_date: date
    weather_text: str
    temperature_min: float
    temperature_max: float
    precipitation_probability_max: int | None
    precipitation_sum: float
    wind_speed_max: float


@dataclass(frozen=True)
class HourlyWeather:
    forecast_time: datetime
    weather_text: str
    temperature: float
    precipitation_probability: int | None
    wind_speed: float


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def is_workday(target_date: date) -> bool:
    return target_date.weekday() < 5


def rain_level_text(weather_code: str | int) -> str:
    return RAIN_LEVEL_BY_CODE.get(str(weather_code), "不下雨")


def rain_status_text(rain_level: str) -> str:
    return "是" if rain_level != "不下雨" else "否"


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def wttr_weather_text(weather_code: str, weather_desc: list[dict[str, str]] | None) -> str:
    mapped_text = WTTR_WEATHER_CODE_TEXT.get(weather_code)
    if mapped_text:
        return mapped_text

    if weather_desc:
        value = weather_desc[0].get("value", "").strip()
        if value:
            return value
    return f"未知天气代码 {weather_code}"


def fetch_wttr_payload() -> dict:
    url = f"https://wttr.in/{urllib.parse.quote(WTTR_LOCATION)}?format=j1"
    return fetch_json(url)


def fetch_forecast(target_date: date) -> Forecast:
    params = {
        "latitude": SHANGHAI_LATITUDE,
        "longitude": SHANGHAI_LONGITUDE,
        "timezone": SHANGHAI_TIMEZONE,
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ]
        ),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    payload = fetch_json(url)

    daily = payload["daily"]
    weather_code = daily["weather_code"][0]
    return Forecast(
        forecast_date=date.fromisoformat(daily["time"][0]),
        weather_text=WEATHER_CODE_TEXT.get(weather_code, f"未知天气代码 {weather_code}"),
        temperature_min=float(daily["temperature_2m_min"][0]),
        temperature_max=float(daily["temperature_2m_max"][0]),
        precipitation_probability_max=daily.get("precipitation_probability_max", [None])[0],
        precipitation_sum=float(daily["precipitation_sum"][0]),
        wind_speed_max=float(daily["wind_speed_10m_max"][0]),
    )


def fetch_forecast_from_wttr(target_date: date) -> Forecast:
    payload = fetch_wttr_payload()
    for item in payload.get("weather", []):
        if item.get("date") != target_date.isoformat():
            continue

        hourly_items = item.get("hourly", [])
        precipitation_probability_max = None
        if hourly_items:
            precipitation_probability_max = max(
                int(hourly.get("chanceofrain", "0")) for hourly in hourly_items
            )
        weather_code = hourly_items[0].get("weatherCode", "") if hourly_items else ""
        weather_desc = hourly_items[0].get("weatherDesc") if hourly_items else None
        precipitation_sum = sum(float(hourly.get("precipMM", "0") or 0) for hourly in hourly_items)
        wind_speed_max = max(float(hourly.get("windspeedKmph", "0") or 0) for hourly in hourly_items)

        return Forecast(
            forecast_date=target_date,
            weather_text=wttr_weather_text(weather_code, weather_desc),
            temperature_min=float(item.get("mintempC", "0") or 0),
            temperature_max=float(item.get("maxtempC", "0") or 0),
            precipitation_probability_max=precipitation_probability_max,
            precipitation_sum=precipitation_sum,
            wind_speed_max=wind_speed_max,
        )

    raise RuntimeError(f"wttr.in 未找到 {target_date.isoformat()} 的天气数据")


def get_forecast(target_date: date) -> Forecast:
    try:
        return fetch_forecast(target_date)
    except Exception:
        return fetch_forecast_from_wttr(target_date)


def fetch_hourly_weather(target_time: datetime) -> HourlyWeather:
    params = {
        "latitude": SHANGHAI_LATITUDE,
        "longitude": SHANGHAI_LONGITUDE,
        "timezone": SHANGHAI_TIMEZONE,
        "start_date": target_time.date().isoformat(),
        "end_date": target_time.date().isoformat(),
        "hourly": ",".join(
            [
                "weather_code",
                "temperature_2m",
                "precipitation_probability",
                "wind_speed_10m",
            ]
        ),
    }
    url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

    payload = fetch_json(url)

    hourly = payload["hourly"]
    target_time_text = target_time.strftime("%Y-%m-%dT%H:00")
    try:
        index = hourly["time"].index(target_time_text)
    except ValueError as exc:
        raise RuntimeError(f"未找到 {target_time_text} 的小时天气数据") from exc

    weather_code = hourly["weather_code"][index]
    precipitation_probability_values = hourly.get("precipitation_probability")
    precipitation_probability = None
    if precipitation_probability_values is not None:
        precipitation_probability = precipitation_probability_values[index]

    return HourlyWeather(
        forecast_time=target_time,
        weather_text=rain_level_text(weather_code),
        temperature=float(hourly["temperature_2m"][index]),
        precipitation_probability=precipitation_probability,
        wind_speed=float(hourly["wind_speed_10m"][index]),
    )


def fetch_hourly_weather_from_wttr(target_time: datetime) -> HourlyWeather:
    payload = fetch_wttr_payload()
    for item in payload.get("weather", []):
        if item.get("date") != target_time.date().isoformat():
            continue

        target_hour = target_time.strftime("%H00").lstrip("0") or "0"
        for hourly in item.get("hourly", []):
            if hourly.get("time") != target_hour:
                continue

            weather_code = hourly.get("weatherCode", "")
            return HourlyWeather(
                forecast_time=target_time,
                weather_text=rain_level_text(weather_code),
                temperature=float(hourly.get("tempC", "0") or 0),
                precipitation_probability=int(hourly.get("chanceofrain", "0") or 0),
                wind_speed=float(hourly.get("windspeedKmph", "0") or 0),
            )

    raise RuntimeError(f"wttr.in 未找到 {target_time.strftime('%Y-%m-%d %H:%M')} 的小时天气数据")


def get_hourly_weather(target_time: datetime) -> HourlyWeather:
    try:
        return fetch_hourly_weather(target_time)
    except Exception:
        return fetch_hourly_weather_from_wttr(target_time)


def build_email(today_weather: HourlyWeather) -> EmailMessage:
    sender = require_env("SMTP_USER")
    recipients = [item.strip() for item in require_env("WEATHER_EMAIL_TO").split(",") if item.strip()]
    if not recipients:
        raise RuntimeError("WEATHER_EMAIL_TO 未配置有效收件人")

    rain_level = today_weather.weather_text
    rain_status = rain_status_text(rain_level)
    rain_level_display = rain_level if rain_status == "是" else "无"
    subject = f"上海今日18:00实时天气 {today_weather.forecast_time.date().isoformat()}"
    body = f"""上海市今日18:00实时天气

今日 18:00 天气
日期：{today_weather.forecast_time.strftime('%Y-%m-%d %H:%M')}
是否下雨：{rain_status}
降雨等级：{rain_level_display}
温度：{today_weather.temperature:.1f}°C

数据来源：Open-Meteo Weather Forecast API（失败时自动回退 wttr.in）
发送时间：{datetime.now(ZoneInfo(SHANGHAI_TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S %Z')}
"""

    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_email(message: EmailMessage) -> None:
    host = require_env("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = require_env("SMTP_USER")
    password = require_env("SMTP_PASSWORD")
    use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() not in {"0", "false", "no"}

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(user, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(user, password)
            server.send_message(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="工作日 16:00 发送上海今日18点实时天气邮件")
    parser.add_argument("--dry-run", action="store_true", help="只打印邮件内容，不发送")
    args = parser.parse_args()

    now = datetime.now(ZoneInfo(SHANGHAI_TIMEZONE))
    today = now.date()
    tomorrow = today + timedelta(days=1)

    if not is_workday(today):
        print(f"{today.isoformat()} 不是工作日，跳过发送。")
        return 0

    today_weather_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
    today_weather = get_hourly_weather(today_weather_time)
    message = build_email(today_weather)
    if args.dry_run:
        print(f"From: {message['From']}")
        print(f"To: {message['To']}")
        print(f"Subject: {message['Subject']}")
        print()
        print(message.get_content())
        return 0

    send_email(message)
    print(f"已发送上海 {today.isoformat()} 18:00 实时天气邮件。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
