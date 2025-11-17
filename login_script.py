import json
import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta
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
    global browser
    page = None
    serviceName = 'ct8' if 'ct8' in panel else 'serv00'
    try:
        if not browser:
            browser = await launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )

        page = await browser.newPage()
        # 设置视口大小，这很重要！
        await page.setViewport({'width': 1366, 'height': 768})
        # 设置用户代理
        await page.setUserAgent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        url = f'https://{panel}/login/?next=/'
        # 使用更严格的等待条件
        await page.goto(url, {'waitUntil': ['domcontentloaded', 'networkidle0']})

        # 等待用户名输入框出现并可见
        await page.waitForSelector('#id_username', {'timeout': 30000})
        username_input = await page.querySelector('#id_username')
        
        # 清空输入框
        await page.evaluate('(input) => input.value = ""', username_input)
        # 输入用户名
        await page.type('#id_username', username, {'delay': 100}) # 添加输入延迟模拟人类

        # 输入密码
        await page.type('#id_password', password, {'delay': 100})

        # 关键修改：等待按钮变为可见和可交互状态
        # 创建一个 Promise race，防止因为某些元素一直加载不成功而卡死
        submit_selector = 'button[type="submit"]'
        print(f"等待提交按钮: {submit_selector}")
        
        # 等待按钮出现在 DOM 中
        await page.waitForSelector(submit_selector, {'timeout': 15000})
        
        # 额外等待确保按钮可见可点击
        await page.waitForFunction(f'''
            document.querySelector('{submit_selector}') &&
            document.querySelector('{submit_selector}').offsetParent !== null &&
            !document.querySelector('{submit_selector}').disabled
        ''', {'timeout': 15000})

        # 使用 JavaScript 直接点击按钮，这通常更可靠
        await page.evaluate(f'''
            document.querySelector('{submit_selector}').click();
        ''')

        # 等待导航完成
        await asyncio.sleep(3)  # 先等待短暂时间
        await page.waitForNavigation({
            'waitUntil': ['networkidle0', 'domcontentloaded'],
            'timeout': 45000
        })

        # 检查是否登录成功
        is_logged_in = await page.evaluate('''() => {
            const logoutButton = document.querySelector('a[href="/logout/"]');
            return logoutButton !== null;
        }''')

        return is_logged_in

    except Exception as e:
        print(f'{serviceName}账号 {username} 登录时出现错误: {e}')
        # 可以在这里添加截图功能帮助调试
        # await page.screenshot({'path': f'error_{username}.png'})
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
        print(f'读取 accounts.json 文件时出错: {e}')
        return

    for account in accounts:
        username = account['username']
        password = account['password']
        panel = account['panel']

        serviceName = 'ct8' if 'ct8' in panel else 'serv00'
        is_logged_in = await login(username, password, panel)

        now_beijing = format_to_iso(datetime.utcnow() + timedelta(hours=8))
        if is_logged_in:
            message += f"✅*{serviceName}*账号 *{username}* 于北京时间 {now_beijing}登录面板成功！\n\n"
            print(f"{serviceName}账号 {username} 于北京时间 {now_beijing}登录面板成功！")
        else:
            message += f"❌*{serviceName}*账号 *{username}* 于北京时间 {now_beijing}登录失败\n\n❗请检查*{username}*账号和密码是否正确。\n\n"
            print(f"{serviceName}账号 {username} 登录失败，请检查{serviceName}账号和密码是否正确。")

        delay = random.randint(1000, 8000)
        await delay_time(delay)
        
    message += f"🔚脚本结束，如有异常点击下方按钮👇"
    await send_telegram_message(message)
    print(f'所有{serviceName}账号登录完成！')
    # 退出时关闭浏览器
    await shutdown_browser()

async def send_telegram_message(message):
    # 使用 Markdown 格式
    formatted_message = f"""
*🎯 serv00&ct8自动化保号脚本运行报告*

🕰 *北京时间*: {format_to_iso(datetime.utcnow() + timedelta(hours=8))}

⏰ *UTC时间*: {format_to_iso(datetime.utcnow())}

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
                        'url': 'https://t.me/yxjsjl'  # 点击按钮后跳转到问题反馈的链接
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
            print(f"发送消息到Telegram失败: {response.text}")
    except Exception as e:
        print(f"发送消息到Telegram时出错: {e}")

if __name__ == '__main__':
    asyncio.run(main())
