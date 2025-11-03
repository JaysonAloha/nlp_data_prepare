# fetch_eastmoney_playwright.py
import re
import json
import sys
import subprocess
from bs4 import BeautifulSoup

URL = "https://stock.eastmoney.com/a/czpnc.html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SELECTOR_TO_WAIT = "ul#newsListContent, div.text, li[id^='newsTr']"

def ensure_playwright_browsers():
    # 尝试运行 playwright install 下载浏览器（如果已安装会快速完成）
    try:
        print("检查并安装 Playwright 浏览器二进制（如果需要）……")
        subprocess.check_call([sys.executable, "-m", "playwright", "install"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("playwright install 执行完毕。")
    except subprocess.CalledProcessError as e:
        print("playwright install 失败，请在终端手动运行: python -m playwright install")
        raise

def fetch_rendered_html(url, timeout=30000):
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception:
        print("缺少 playwright 库，请先运行: pip install playwright bs4")
        raise

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            try:
                page.wait_for_selector(SELECTOR_TO_WAIT, timeout=8000)
            except PlaywrightTimeoutError:
                page.wait_for_load_state("networkidle", timeout=10000)
            html = page.content()
        finally:
            try:
                context.close()
            except:
                pass
            browser.close()
    return html

def parse_mapping(html):
    soup = BeautifulSoup(html, "lxml")
    mapping = {}
    candidates = []
    for li in soup.select("ul#newsListContent > li"):
        div = li.find("div", class_="text")
        if div:
            candidates.append(div)
        else:
            candidates.append(li)
    if not candidates:
        candidates = soup.find_all("div", class_="text")
    for container in candidates:
        title_p = container.find("p", class_="title")
        if not title_p:
            continue
        a_tag = title_p.find("a", href=True)
        if not a_tag:
            continue
        href = a_tag["href"].strip()
        time_p = container.find("p", class_="time")
        if not time_p:
            continue
        time_text = time_p.get_text(strip=True)
        m = re.search(r"(\d{4}年\d{2}月\d{2}日)", time_text)
        if not m:
            continue
        date_key = m.group(1)
        if date_key not in mapping:
            mapping[date_key] = href
    return mapping

def main(url):
    try:
        # 尝试直接渲染一次；若失败并提示浏览器缺失，则尝试安装
        try:
            html = fetch_rendered_html(url)
        except Exception as e:
            # 如果错误提示为浏览器可执行文件不存在，尝试安装浏览器并重试
            err_msg = str(e)
            if "Executable doesn't exist" in err_msg or "playwright" in err_msg.lower():
                ensure_playwright_browsers()
                html = fetch_rendered_html(url)
            else:
                raise
        mapping = parse_mapping(html)
        return mapping
        #print(json.dumps(mapping, ensure_ascii=False, indent=2))

    except Exception as e:
        print("运行失败：", e)
        sys.exit(1)

if __name__ == '__main__':
    dic=main(URL)
    print(len(dic))
    print(dic)