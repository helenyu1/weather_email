# 上海工作日天气邮件

仅在工作日的 16:00 发送邮件，内容包含上海当天 18:00 的实时天气和温度，以及明天的天气和温度预报。

天气数据来源：Open-Meteo，无需 API Key；如果主接口失败，会自动回退到 wttr.in。

支持两种运行方式：

- 本地 macOS `launchd` 定时运行
- GitHub Actions 云端定时运行

## 配置

复制示例配置并填写真实邮箱信息：

```bash
cp env.example .env
```

需要配置：

- `SMTP_HOST`：SMTP 服务器，例如 QQ 邮箱可用 `smtp.qq.com`
- `SMTP_PORT`：SMTP 端口，例如 `587`
- `SMTP_USE_SSL`：是否直连 SSL；如果使用 `587 + STARTTLS`，这里填 `false`
- `SMTP_USER`：发件邮箱，例如 `your_name@qq.com`
- `SMTP_PASSWORD`：邮箱授权码或 SMTP 密码
- `WEATHER_EMAIL_TO`：收件邮箱，多个用英文逗号分隔，格式如 `a@example.com,b@example.com`

当前常用配置示例：

```env
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USE_SSL=false
SMTP_USER=your_name@qq.com
SMTP_PASSWORD=your_smtp_authorization_code
WEATHER_EMAIL_TO=a@example.com,b@example.com
```

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

如果当天不是工作日，脚本会直接跳过发送。

真实发送：

```bash
python3 daily_shanghai_weather.py
```

## GitHub Actions 定时任务

项目内已包含 `.github/workflows/daily-weather-email.yml`，默认每天 `16:00` 上海时间运行；脚本内部会在周末自动跳过。

GitHub Actions 的 cron 使用 UTC，所以 workflow 中配置的是 `08:00 UTC`。

如果你需要更准时，优先考虑本机 `launchd`、自托管 runner，或者由你自己的服务器 cron 去触发 GitHub workflow。GitHub Actions 的定时任务本身可能会有几分钟到十几分钟的延迟。

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

默认配置为每天 `16:00` 运行；脚本内部会在周末自动跳过。

## 安全说明

- 不要提交 `.env`。
- 不要把邮箱授权码写进 README、代码或公开 issue。
- GitHub Actions 使用 Secrets 保存 SMTP 密码。
- `env.example` 只保留占位示例，可以安全分享。
