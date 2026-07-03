# 上海明日天气邮件

每天下午 6 点前获取上海市明天的天气预报，并发送邮件到指定邮箱。

天气数据来源：Open-Meteo，无需 API Key。

支持两种运行方式：

- 本地 macOS `launchd` 定时运行
- GitHub Actions 云端定时运行

## 配置

复制示例配置并填写真实邮箱信息：

```bash
cp env.example .env
```

需要配置：

- `SMTP_HOST`：SMTP 服务器，例如 `smtp.qq.com`
- `SMTP_PORT`：SSL 通常是 `465`
- `SMTP_USE_SSL`：默认 `true`
- `SMTP_USER`：发件邮箱
- `SMTP_PASSWORD`：邮箱授权码或 SMTP 密码
- `WEATHER_EMAIL_TO`：收件邮箱，多个用英文逗号分隔

## 手动测试

先加载环境变量：

```bash
set -a
source .env
set +a
```

只打印邮件内容，不发送：

```bash
python3 daily_shanghai_weather.py --dry-run
```

真实发送：

```bash
python3 daily_shanghai_weather.py
```

## GitHub Actions 定时任务

项目内已包含 `.github/workflows/daily-weather-email.yml`，默认每天 `17:50` 上海时间运行。

GitHub Actions 的 cron 使用 UTC，所以 workflow 中配置的是 `09:50 UTC`。

需要在 GitHub 仓库中配置 Secrets：

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USE_SSL`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `WEATHER_EMAIL_TO`

配置路径：`Settings` -> `Secrets and variables` -> `Actions`。

手动测试 workflow：进入 GitHub Actions 页面，选择 `Daily Shanghai Weather Email`，点击 `Run workflow`。

## macOS 定时任务

1. 修改 `com.local.shanghai-weather-email.plist` 中的 `/ABSOLUTE/PATH/TO/weather_email` 为本项目真实绝对路径。
2. 确认 `.env` 已填写真实邮箱配置。
3. 安装定时任务：

```bash
cp com.local.shanghai-weather-email.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.shanghai-weather-email.plist
```

默认配置为每天 `17:50` 运行。

## 安全说明

- 不要提交 `.env`。
- 不要把邮箱授权码写进 README、代码或公开 issue。
- GitHub Actions 使用 Secrets 保存 SMTP 密码。
- `env.example` 只保留占位示例，可以安全分享。
