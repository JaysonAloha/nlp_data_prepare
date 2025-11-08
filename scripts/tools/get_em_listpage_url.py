import re
import sys
import subprocess
from bs4 import BeautifulSoup


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SELECTOR_TO_WAIT = "ul#newsListContent, div.text, li[id^='newsTr']"
FINANCE_BREAKFAST_KEYWORD = "财经早餐"  # 筛选关键词


def ensure_playwright_browsers():
    try:
        print("检查并安装 Playwright 浏览器（如需）……")
        subprocess.check_call(
            [sys.executable, "-m", "playwright", "install"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        print("请手动安装浏览器：python -m playwright install")
        raise

def fetch_rendered_html(url):
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        print("请安装依赖：pip install playwright bs4")
        raise

    # 延长超时时间（单位：毫秒）
    GOTO_TIMEOUT = 6000000  # 页面加载超时（1分钟）
    SELECTOR_TIMEOUT = 6000000  # 元素等待超时（1分钟）

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="zh-CN")
        page = context.new_page()
        try:
            # 延长页面加载超时
            page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT)
            try:
                # 延长元素等待超时
                page.wait_for_selector(SELECTOR_TO_WAIT, timeout=SELECTOR_TIMEOUT)
            except PlaywrightTimeoutError:
                # 网络空闲状态也延长超时
                page.wait_for_load_state("networkidle", timeout=SELECTOR_TIMEOUT)
            return page.content()
        finally:
            context.close()
            browser.close()

def parse_mapping(html):
    soup = BeautifulSoup(html, "lxml")
    mapping = {}
    candidates = []

    # 收集可能的新闻容器
    for li in soup.select("ul#newsListContent > li"):
        div = li.find("div", class_="text")
        candidates.append(div if div else li)
    if not candidates:
        candidates = soup.find_all("div", class_="text")

    # 提取含"财经早餐"的链接和日期
    for container in candidates:
        title_p = container.find("p", class_="title")
        if not title_p:
            continue

        a_tag = title_p.find("a", href=True)
        if not a_tag:
            continue

        # 筛选标题包含"财经早餐"的链接
        title_text = a_tag.get_text(strip=True)
        if FINANCE_BREAKFAST_KEYWORD not in title_text:
            continue

        # 处理链接（补全相对路径）
        href = a_tag["href"].strip()
        if not href.startswith(("http://", "https://")):
            href = "https://finance.eastmoney.com" + href

        # 提取日期
        time_p = container.find("p", class_="time")
        if not time_p:
            continue

        date_match = re.search(r"(\d{4}年\d{2}月\d{2}日)", time_p.get_text(strip=True))
        if date_match:
            date_key = date_match.group(1)
            if date_key not in mapping:
                mapping[date_key] = href

    return mapping


def get_em_listpage_url(url):
    try:
        try:
            html = fetch_rendered_html(url)
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright" in str(e).lower():
                ensure_playwright_browsers()
                html = fetch_rendered_html(url)
            else:
                raise
        return parse_mapping(html)
    except Exception as e:
        print(f"运行失败：{e}")
        sys.exit(1)

