import os
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError

DEBUG = os.environ.get("DEBUG", "0") == "1"


def login_and_sign():
    username = os.environ.get("YCOONAME")
    password = os.environ.get("YCOOPWD")

    if not username or not password:
        print("[-] 请设置环境变量 ycooname (用户名) 和 ycoopwd (密码)")
        print("    export ycooname=你的用户名")
        print("    export ycoopwd=你的密码")
        sys.exit(1)

    print(f"[*] 正在登录账号: {username}")

    with sync_playwright() as p:
        print("[系统] 启动浏览器")
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors",
                "--ignore-certificate-errors-spki-list",
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
            print("[*] 访问首页")
            page.goto("https://ycoo.net/", timeout=30000)
            page.wait_for_timeout(3000)

            print("[*] 点击登录链接，打开登录弹窗")
            page.click('a[href*="mod=logging&action=login"]')
            page.wait_for_timeout(3000)

            print("[*] 查找并填写用户名")
            page.wait_for_selector('input[name="username"]', timeout=10000)
            page.fill('input[name="username"]', username)

            print("[*] 填写密码")
            page.fill('input[name="password"]', password)

            print("[*] 点击登录按钮")
            page.click('button[name="loginsubmit"], button[type="submit"]:has-text("登录")')

            page.wait_for_timeout(5000)

            current_url = page.url
            page_content = page.content()

            if "登录失败" in page_content or "密码错误" in page_content or "错误" in page_content:
                error_msg = ""
                try:
                    error_el = page.query_selector('.alert_error, .show_error, #messagetext, .pc_inner')
                    if error_el:
                        error_msg = error_el.inner_text().strip()
                except:
                    pass
                if not error_msg:
                    import re
                    m = re.search(r'登录失败[^<]+', page_content)
                    if m:
                        error_msg = m.group(0)
                print(f"[-] 登录失败: {error_msg[:100] if error_msg else '未知错误'}")
                browser.close()
                return False

            if "欢迎您" in page_content or "登录成功" in page_content or username in page_content:
                print("[+] 登录成功!")
            elif page.query_selector('text=退出'):
                print("[+] 登录成功 (检测到退出按钮)!")
            elif "首页" in current_url or "portal" in current_url or "forum" in current_url:
                print("[+] 登录成功 (已跳转到首页)!")
            else:
                print(f"[*] 当前URL: {current_url}")
                print("[-] 登录状态未知")
                browser.close()
                return False

            print("[*] 访问签到页面")
            page.goto("https://ycoo.net/k_misign-sign.html", timeout=30000)
            page.wait_for_timeout(3000)

            page_content = page.content()

            is_signed = False
            sign_status = ""

            if any(kw in page_content for kw in ["您今天已经签到", "今日已签到", "已经签到", "已签到"]):
                is_signed = True
                sign_status = "检测到已签到文字"

            visited_btn = page.query_selector('.btn.btnvisted')
            if visited_btn:
                is_signed = True
                sign_status = "检测到已签到按钮状态 (btnvisted)"
                if DEBUG:
                    print("[DEBUG] 找到 .btn.btnvisted 元素（已签到状态）")

            qiandaobtnnum = page.query_selector('#qiandaobtnnum')
            if qiandaobtnnum:
                btn_num = qiandaobtnnum.get_attribute('value') or ''
                if DEBUG:
                    print(f"[DEBUG] 签到排名: {btn_num}")
                if btn_num and btn_num.isdigit() and int(btn_num) > 0:
                    is_signed = True
                    if not sign_status:
                        sign_status = f"签到排名: {btn_num}"

            font_div = page.query_selector('.paiming .font')
            if font_div:
                font_text = font_div.inner_text().strip()
                if DEBUG:
                    print(f"[DEBUG] 状态文字: {font_text}")
                if "签到排名" in font_text:
                    is_signed = True
                    if not sign_status:
                        sign_status = font_text

            sign_button = page.query_selector('#JD_sign')
            if sign_button:
                btn_text = sign_button.inner_text().strip()
                btn_href = sign_button.get_attribute('href') or ''
                btn_class = sign_button.get_attribute('class') or ''

                if DEBUG:
                    print(f"[DEBUG] 签到按钮文字: '{btn_text}'")
                    print(f"[DEBUG] 签到按钮href: {btn_href}")
                    print(f"[DEBUG] 签到按钮class: {btn_class}")

                if "login" in btn_href:
                    print("[-] 未登录状态，无法签到")
                    browser.close()
                    return False

                if btn_text and any(kw in btn_text for kw in ["天", "已", "签", "连续", "Lv", "lv", "等级"]):
                    is_signed = True
                    sign_status = f"签到按钮显示: {btn_text}"

            if is_signed:
                print(f"[+] 今天已经签到过了! ({sign_status})")
                browser.close()
                return True

            print("[*] 查找签到按钮")
            if sign_button:
                print("[*] 点击签到按钮")
                sign_button.click()
                page.wait_for_timeout(5000)

                page_content = page.content()
                if "签到成功" in page_content or "签到奖励" in page_content or "恭喜" in page_content:
                    print("[+] 签到成功!")
                    browser.close()
                    return True
                elif "您今天已经签到" in page_content or "今日已签到" in page_content:
                    print("[+] 今天已经签到过了!")
                    browser.close()
                    return True
                else:
                    try:
                        sign_text = page.query_selector('.qiandao_success, .sign_success, .alert_right, .pc_inner')
                        if sign_text:
                            msg = sign_text.inner_text().strip()
                            print(f"[+] 签到结果: {msg[:200]}")
                            browser.close()
                            return True
                    except:
                        pass

                    print("[?] 签到结果未知，请检查页面")
                    if DEBUG:
                        print(f"[DEBUG] 页面内容: {page_content[:500]}")
            else:
                print("[+] 今天已经签到过了! (签到按钮已消失)")
                if DEBUG:
                    page_content = page.content()
                    print(f"[DEBUG] 页面内容: {page_content[:500]}")
                browser.close()
                return True

            browser.close()
            return False

        except TimeoutError as e:
            print(f"[-] 页面加载超时: {e}")
            browser.close()
            return False
        except Exception as e:
            print(f"[-] 发生错误: {e}")
            browser.close()
            return False


if __name__ == "__main__":
    try:
        success = login_and_sign()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[!] 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"[-] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
