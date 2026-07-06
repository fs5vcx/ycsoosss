import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError

DEBUG = os.environ.get("DEBUG", "0") == "1"


def login_and_sign():
    username = os.environ.get("YCOONAME")
    password = os.environ.get("YCOOPWD")

    if not username or not password:
        print("[-] 请设置环境变量 YCOONAME 和 YCOOPWD")
        sys.exit(1)

    print(f"[*] 正在登录账号: {username}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors",
                "--disable-infobars",
                "--window-size=1280,800",
                "--use-gl=swiftshader",
            ]
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )

        page = context.new_page()

        try:
            print("[*] 打开首页")
            page.goto("https://ycoo.net/", timeout=30000)
            page.wait_for_timeout(1500)

            print("[*] 打开登录弹窗")
            page.click('a[href*="mod=logging&action=login"]')
            page.wait_for_timeout(1500)

            print("[*] 输入用户名密码")
            page.fill('input[name="username"]', username)
            page.fill('input[name="password"]', password)

            print("[*] 点击登录按钮")
            page.click('button[name="loginsubmit"], button[type="submit"]:has-text("登录")')
            page.wait_for_timeout(3000)

            page_content = page.content()

            # 登录失败判断
            if any(kw in page_content for kw in ["密码错误", "登录失败", "错误"]):
                print("[-] 登录失败")
                browser.close()
                return False

            # 登录成功判断
            if "退出" in page_content or username in page_content:
                print("[+] 登录成功")
            else:
                print("[-] 登录状态未知")
                browser.close()
                return False

            print("[*] 打开签到页面")
            page.goto("https://ycoo.net/k_misign-sign.html", timeout=30000)
            page.wait_for_timeout(1500)

            page_content = page.content()

            # --- 已签到判断（只保留“您今天已经签到”和按钮状态） ---
            if "您今天已经签到" in page_content:
                print("[+] 今天已经签到过了（文字判断）")
                browser.close()
                return True

            if page.query_selector(".btn.btnvisted"):
                print("[+] 今天已经签到过了（按钮状态）")
                browser.close()
                return True

            # --- 处理遮罩层 ---
            shade = page.query_selector("#layui-layer-shade1")
            if shade:
                print("[*] 检测到遮罩层，强制关闭")
                page.evaluate("document.getElementById('layui-layer-shade1').remove();")
                page.wait_for_timeout(500)

            # --- 未签到：必须点击按钮 ---
            sign_button = page.query_selector("#JD_sign")

            if sign_button:
                print("[*] 检测到签到按钮，开始签到")

                # 再次检查遮罩层
                shade = page.query_selector("#layui-layer-shade1")
                if shade:
                    print("[*] 遮罩层再次出现，强制关闭")
                    page.evaluate("document.getElementById('layui-layer-shade1').remove();")
                    page.wait_for_timeout(300)

                sign_button.click()
                page.wait_for_timeout(3000)

                page_content = page.content()

                if any(kw in page_content for kw in ["签到成功", "签到奖励", "恭喜"]):
                    print("[+] 签到成功!")
                    browser.close()
                    return True

                print("[?] 签到结果未知，但按钮已点击")
                browser.close()
                return True

            # 按钮不存在 → 已签到
            print("[+] 今天已经签到过了（按钮不存在）")
            browser.close()
            return True

        except Exception as e:
            print(f"[-] 错误: {e}")
            browser.close()
            return False


if __name__ == "__main__":
    try:
        success = login_and_sign()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[!] 用户中断")
        sys.exit(130)
