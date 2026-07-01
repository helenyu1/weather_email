#!/usr/bin/env python3
"""Send tomorrow's Shanghai workday weather forecast by email."""

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


@dataclass(frozen=True)
class Forecast:
    forecast_date: date
    weather_text: str
    temperature_min: float
    temperature_max: float
    precipitation_probability_max: int | None
    precipitation_sum: float
    wind_speed_max: float


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"缺少环境变量: {name}")
    return value


def is_workday(target_date: date) -> bool:
    holidays = parse_date_set(os.getenv("WEATHER_EMAIL_HOLIDAYS", ""))
    extra_workdays = parse_date_set(os.getenv("WEATHER_EMAIL_EXTRA_WORKDAYS", ""))

    if target_date in extra_workdays:
        return True
    if target_date in holidays:
        return False
    return target_date.weekday() < 5


def parse_date_set(raw_value: str) -> set[date]:
    result: set[date] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        result.add(date.fromisoformat(item))
    return result


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

    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

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


def build_email(forecast: Forecast) -> EmailMessage:
    sender = require_env("SMTP_USER")
    recipients = [item.strip() for item in require_env("WEATHER_EMAIL_TO").split(",") if item.strip()]
    if not recipients:
        raise RuntimeError("WEATHER_EMAIL_TO 未配置有效收件人")

    probability = forecast.precipitation_probability_max
    probability_text = "暂无数据" if probability is None else f"{probability}%"
    subject = f"上海明日工作日天气 {forecast.forecast_date.isoformat()}"
    body = f"""上海市明日工作日天气预报

日期：{forecast.forecast_date.isoformat()}
天气：{forecast.weather_text}
温度：{forecast.temperature_min:.1f}°C - {forecast.temperature_max:.1f}°C
最高降水概率：{probability_text}
预计降水量：{forecast.precipitation_sum:.1f} mm
最大风速：{forecast.wind_speed_max:.1f} km/h

数据来源：Open-Meteo Weather Forecast API
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
    parser = argparse.ArgumentParser(description="发送上海明日工作日天气邮件")
    parser.add_argument("--dry-run", action="store_true", help="只打印邮件内容，不发送")
    parser.add_argument("--force", action="store_true", help="即使明天不是工作日也发送")
    args = parser.parse_args()

    tomorrow = datetime.now(ZoneInfo(SHANGHAI_TIMEZONE)).date() + timedelta(days=1)
    if not args.force and not is_workday(tomorrow):
        print(f"{tomorrow.isoformat()} 不是工作日，跳过发送。")
        return 0

    forecast = fetch_forecast(tomorrow)
    message = build_email(forecast)
    if args.dry_run:
        print(f"From: {message['From']}")
        print(f"To: {message['To']}")
        print(f"Subject: {message['Subject']}")
        print()
        print(message.get_content())
        return 0

    send_email(message)
    print(f"已发送上海 {tomorrow.isoformat()} 天气邮件。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
