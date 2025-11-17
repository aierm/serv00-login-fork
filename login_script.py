import json
import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta, timezone
import aiofiles
import random
import requests
import os

# 从环境变量中获取 Telegram Bot Token 和 Chat ID
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def format_to_iso(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')

async def delay_time(ms):
    await asyncio.sleep(ms / 1000)

# 全局浏览器实例
browser = None

# telegram消息
message = ""

async def login(username, password, panel):
    """
    登录 serv00/ct8 面板，返回 True/False
    """
    global browser
    serviceName = 'ct8' if 'ct8' in panel else 'serv00'
    page = None

    try:
        if not browser:
            browser = await launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )

        page = await browser.newPage()
        url = f'https://{panel}/login/?next=/'
        print(f"[INFO] 打开登录页面: {url}")
        await page.goto(url)

        # 输入用户名
        await page.waitForSelector('input[name="login"]', {'visible': True, 'timeout': 15000})
        await page.type('input[name="login"]', username)
        print(f"[DEBUG] 输入用户名: {username}")

        # 输入密码
        await page.waitForSelector('input[name="password"]', {'visible': True, 'timeout': 15000})
        await page.type('input[name="password"]', password)
        print(f"[DEBUG] 输入密码: {'*' * len(password)}")

        # 点击提交
        await page.waitForSelector('button[type="submit"]', {'visible': True, 'timeout': 15000})
        await page.click('button[type="submit"]')
        print("[DEBUG] 点击登录按钮")

        # 等待登录成功标志（退出按钮）
        try:
            await page.waitForSelector('a[href="/logout/"]', {'timeout': 15000})
            print(f"[SUCCESS] {serviceName}账号 {username} 登录成功")
            return True
        except asyncio.TimeoutError:
            print(f"[FAIL] {serviceName}账号 {username} 登录超时或失败")
            return False

    except Exception as e:
        print(f"{serviceName}账号 {username} 登录时出现错误: {e}")
        return False

    finally:
        if page:
            await page.close()

# 显式的浏览器关闭函数
async def shutdown_browser():
    global browser
    if browser:
        await browser.close()
        browser = None

async def main():
    global message

    try:
        async with aiofiles.open('accounts.json', mode='r', encoding='utf-8') as f:
            accounts_json = await f.read()
        accounts = json.loads(accounts_json)
    except Exception as e:
        print(f"读取 accounts.json 文件时出错: {e}")
        return

    for account in accounts:
        username = account['username']
        password = account['password']
        panel = account['panel']

        serviceName = 'ct8' if 'ct8' in panel else 'serv00'
        is_logged_in = await login(username, password, panel)

        # 改为 timezone-aware 时间
        utc_now = datetime.now(timezone.utc)
        beijing_now = utc_now.astimezone(timezone(timedelta(hours=8)))

        if is_logged_in:
            message += f"✅ *{serviceName}*账号 *{username}* 于北京时间 {format_to_iso(beijing_now)} 登录面板成功！\n\n"
            print(f"{serviceName}账号 {username} 于北京时间 {format_to_iso(beijing_now)} 登录面板成功！")
        else:
            message += f"❌ *{serviceName}*账号 *{username}* 于北京时间 {format_to_iso(beijing_now)} 登录失败\n\n❗ 请检查*{username}*账号和密码是否正确。\n\n"
            print(f"{serviceName}账号 {username} 登录失败，请检查{serviceName}账号和密码是否正确。")

        delay = random.randint(1000, 8000)
        await delay_time(delay)

    message += f"🔚 脚本结束，如有异常点击下方按钮👇"
    await send_telegram_message(message)
    print(f"所有账号登录完成！")

    # 退出时关闭浏览器
    await shutdown_browser()

async def send_telegram_message(message):
    # 使用 Markdown 格式
    utc_now = datetime.now(timezone.utc)
    beijing_now = utc_now.astimezone(timezone(timedelta(hours=8)))

    formatted_message = f"""
*🎯 serv00&ct8自动化保号脚本运行报告*

🕰 *北京时间*: {format_to_iso(beijing_now)}
⏰ *UTC时间*: {format_to_iso(utc_now)}

📝 *任务报告*:

{message}
    """

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': formatted_message,
        'parse_mode': 'Markdown',  # 使用 Markdown 格式
        'reply_markup': {
            'inline_keyboard': [
                [
                    {
                        'text': '问题反馈❓',
                        'url': 'https://t.me/yxjsjl'
                    }
                ]
            ]
        }
    }
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"发送消息到 Telegram 失败: {response.text}")
    except Exception as e:
        print(f"发送消息到 Telegram 时出错: {e}")

if __name__ == '__main__':
    asyncio.run(main())
