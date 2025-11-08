import os
import json
from os.path import exists
import pandas as pd
import time
import random as rd
from urllib.parse import urlparse
from datetime import date,datetime, timedelta
from scripts.logging_config import setup_logger
import requests
from bs4 import BeautifulSoup
import re
import sys
import subprocess
from get_em_listpage_url import get_em_listpage_url
from get_em_calendar_image import get_finance_calendar_image

logger=setup_logger("eastmoney_breakfast")

em_dir=os.path.join("cache","news","eastmoney_breakfast")
em_urls_path = os.path.join(em_dir, "urls_of_em.json")
em_breakfast_path=os.path.join(em_dir, "breakfast.json")
em_calendar_pic_path=os.path.join(em_dir, "calendar_pic_url.json")

# 确保目录存在
os.makedirs(em_dir, exist_ok=True)


def is_a_stock_trading_day(check_date):
    """
    判断2022年11月-2025年期间A股是否为交易日
    :param check_date: 待判断日期（date或datetime对象）
    :return: True为交易日，False为休市；超出范围返回None
    """
    if isinstance(check_date, datetime):
        check_date = check_date.date()

    start_date = date(2022, 11, 1)
    end_date = date(2025, 12, 31)
    if not (start_date <= check_date <= end_date):
        return None

    weekday = check_date.weekday()  # 0=周一，5=周六，6=周日
    if weekday in (5, 6):
        return False

    # 2. 各年份休市日期（整理自上交所/深交所公告）
    # 2022年11-12月休市日期
    closed_2022 = [
        date(2022, 12, 31),  # 周六（周末休市）
        # 注：2022年11-12月无额外法定节假日休市，仅周末休市
    ]

    # 2023年休市日期
    closed_2023 = [
        # 元旦：2023-01-01（周日）休市，1月2日补休休市
        date(2023, 1, 1), date(2023, 1, 2),
        # 春节：1月21日（除夕）-1月27日休市
        date(2023, 1, 21), date(2023, 1, 22), date(2023, 1, 23),
        date(2023, 1, 24), date(2023, 1, 25), date(2023, 1, 26), date(2023, 1, 27),
        # 清明节：4月5日（周三）休市
        date(2023, 4, 5),
        # 劳动节：4月29日-5月3日休市
        date(2023, 4, 29), date(2023, 4, 30), date(2023, 5, 1),
        date(2023, 5, 2), date(2023, 5, 3),
        # 端午节：6月22日-6月24日休市
        date(2023, 6, 22), date(2023, 6, 23), date(2023, 6, 24),
        # 中秋节+国庆节：9月29日-10月6日休市
        date(2023, 9, 29), date(2023, 9, 30), date(2023, 10, 1),
        date(2023, 10, 2), date(2023, 10, 3), date(2023, 10, 4),
        date(2023, 10, 5), date(2023, 10, 6)
    ]

    # 2024年休市日期
    closed_2024 = [
        # 元旦：1月1日（周一）休市
        date(2024, 1, 1),
        # 春节：2月10日（除夕）-2月17日休市
        date(2024, 2, 10), date(2024, 2, 11), date(2024, 2, 12),
        date(2024, 2, 13), date(2024, 2, 14), date(2024, 2, 15),
        date(2024, 2, 16), date(2024, 2, 17),
        # 清明节：4月4日（周四）休市
        date(2024, 4, 4),
        # 劳动节：5月1日-5月5日休市
        date(2024, 5, 1), date(2024, 5, 2), date(2024, 5, 3),
        date(2024, 5, 4), date(2024, 5, 5),
        # 端午节：6月10日（周一）休市
        date(2024, 6, 10),
        # 中秋节：9月17日（周二）休市
        date(2024, 9, 17),
        # 国庆节：10月1日-10月7日休市
        date(2024, 10, 1), date(2024, 10, 2), date(2024, 10, 3),
        date(2024, 10, 4), date(2024, 10, 5), date(2024, 10, 6), date(2024, 10, 7)
    ]

    # 2025年预估休市日期（以当年交易所公告为准）
    closed_2025 = [
        # 元旦：1月1日（周三）休市
        date(2025, 1, 1),
        # 春节：1月28日（除夕）-2月3日休市
        date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
        date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2), date(2025, 2, 3),
        # 清明节：4月4日（周五）休市
        date(2025, 4, 4),
        # 劳动节：5月1日-5月5日休市
        date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3),
        date(2025, 5, 4), date(2025, 5, 5),
        # 端午节：6月1日（周日）+6月2日（周一）休市
        date(2025, 6, 1), date(2025, 6, 2),
        # 中秋节：9月8日（周二）休市
        date(2025, 9, 8),
        # 国庆节：10月1日-10月7日休市
        date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3),
        date(2025, 10, 4), date(2025, 10, 5), date(2025, 10, 6), date(2025, 10, 7)
    ]

    # 3. 根据年份匹配休市列表
    year = check_date.year
    if year == 2022:
        closed_days = closed_2022
    elif year == 2023:
        closed_days = closed_2023
    elif year == 2024:
        closed_days = closed_2024
    elif year == 2025:
        closed_days = closed_2025
    else:
        return None  # 超出范围

    # 4. 最终判断：不在休市列表中则为交易日
    return check_date not in closed_days

def get_adjusted_workday(date_input = None) -> date:
    """
    根据规则获取调整后的工作日（仅返回年月日的date类型）：
    - 未输入日期或输入日期是当日：用当前时间判断，早于10点则基准为前一天，否则为当天；
    - 输入日期是历史日期（非当日）：忽略具体时间，仅用其年月日作为基准；
    - 基准日期为工作日则返回，否则返回上一个工作日（仅含年月日）。
    """
    today = datetime.now().date()
    now = datetime.now()

    if date_input is None:
        base_date = (now - timedelta(days=1)).date() if now.hour < 10 else today
    else:
        input_date = date_input.date() if isinstance(date_input, datetime) else date_input
        if input_date == today:
            base_date = (now - timedelta(days=1)).date() if now.hour < 10 else today
        else:
            base_date = input_date

    if is_a_stock_trading_day(base_date):
        return base_date
    else:
        current_date = base_date - timedelta(days=1)
        while not is_a_stock_trading_day(current_date):
            current_date -= timedelta(days=1)
        return current_date

#返回东方财富财经早餐的列表网页链接
def get_eastmoney_url(end_date = None) :
    end_date=get_adjusted_workday(end_date)
    start_date=date(year=2022,month=11,day=2)
    # 计算工作日总数
    date_range = pd.date_range(start=start_date, end=end_date)
    workday_count = sum(1 for d in date_range if is_a_stock_trading_day(d.date()))

    # 生成URL列表（修复分页逻辑）
    urls = ["https://stock.eastmoney.com/a/czpnc.html"]  # 第一页
    total_pages = (workday_count + 19) // 20  # 向上取整，避免漏页
    for i in range(2, total_pages + 1):
        url = f"https://stock.eastmoney.com/a/czpnc_{i}.html"  # 修复拼接格式（下划线）
        urls.append(url)

    # 写入JSON文件（修复文件模式和序列化问题）
    urls_dic = {
        "end_date": end_date.isoformat(),  # date类型转字符串（JSON可序列化）
        "urls": urls  # 补充URL列表到字典
    }
    try:
        with open(em_urls_path, "w", encoding="utf-8") as f:
            json.dump(urls_dic, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"文件写入失败：{e}")  # 增加异常捕获

    return None

#读取列表网页链接，返回每个工作日的财经早餐网页链接
def get_em_url_page(end_date = None) :
    if not exists(em_urls_path):
        get_eastmoney_url(end_date)

    with open(em_urls_path, "r", encoding="utf-8") as f:
        urls_dic = json.load(f)
        last_date_str = urls_dic["end_date"]
        urls = urls_dic["urls"]
        last_date = datetime.fromisoformat(last_date_str).date()
    if last_date < end_date:
        get_eastmoney_url(end_date)
        with open(em_urls_path, "r", encoding="utf-8") as f:
            urls_dic = json.load(f)
            last_date = urls_dic["end_date"]
            urls = urls_dic["urls"]

    date_and_urls={}
    for url in urls:
        time.sleep(rd.uniform(2, 5))
        html=get_em_listpage_url(url)
        date_and_urls.update(html)

    #保存每日财经早餐的网页链接
    with open(em_breakfast_path,"w",encoding="utf-8") as f:
        json.dump(date_and_urls,f, ensure_ascii=False, indent=2)

    return None

#根据每日财经早餐的链接，找到里面的图片并保存
def get_calendar_pic(end_date=None) :
    if not exists(em_urls_path):
        get_eastmoney_url(end_date)

    with open(em_urls_path,"r",encoding="utf-8") as f:
        data_dic=json.load(f)
    last_date_str=max(data_dic.keys())
    last_date = datetime.fromisoformat(last_date_str).date()

    if last_date < end_date:
        get_eastmoney_url(end_date)
        with open(em_urls_path,"r",encoding="utf-8") as f:
            data_dic=json.load(f)

    calendar_dic={}
    for date_url in data_dic.items():
        date_calendar=date_url[0]
        url=date_url[1]
        calendar_url=get_finance_calendar_image(url)
        calendar_dic[date_calendar]=calendar_url

    with open(em_calendar_pic_path,"w",encoding="utf-8") as f:
        json.dump(calendar_dic, f, ensure_ascii=False, indent=2)
    return None

def fetch_em_list_pages(urls):
    """爬取指定的列表页URLs，返回日期到详情页链接的映射"""
    date_and_urls = {}
    for url in urls:
        time.sleep(rd.uniform(2, 5))
        try:
            page_data = get_em_listpage_url(url)
            date_and_urls.update(page_data)
        except Exception as e:
            logger.error(f"爬取列表页 {url} 失败: {e}")
    return date_and_urls


def get_specific_date_breakfast(specific_date):
    """
    获取特定日期的财经早餐网页链接和图片链接

    Args:
        specific_date: 特定日期，可为date对象或"YYYY-MM-DD"格式字符串

    Returns:
        包含日期、网页链接和图片链接的字典，格式:
        {"date": "YYYY年MM月DD日", "page_url": str, "calendar_url": str}
        若未找到对应数据，对应值为None
    """
    # 处理输入日期格式
    try:
        if isinstance(specific_date, str):
            # 解析字符串格式日期为date对象
            specific_date = datetime.strptime(specific_date, "%Y-%m-%d").date()
        elif not isinstance(specific_date, date):
            logger.error("输入日期必须是date对象或'YYYY-MM-DD'格式字符串")
            return None
    except ValueError as e:
        logger.error(f"日期格式错误: {e}")
        return None

    start_date = date(year=2022, month=11, day=2)
    # 检查特定日期是否在起始日期之前
    if specific_date < start_date:
        logger.error(f"特定日期 {specific_date} 早于起始日期 {start_date}，无数据")
        return {"date": specific_date.strftime("%Y年%m月%d日"), "page_url": None, "calendar_url": None}

    # 转换为目标日期字符串（YYYY年MM月DD日）
    target_date_str = specific_date.strftime("%Y年%m月%d日")

    # 计算从起始日期到特定日期的工作日数量，确定该日期是第几个工作日
    date_range = pd.date_range(start=start_date, end=specific_date)
    workdays = [d.date() for d in date_range if is_a_stock_trading_day(d.date())]
    n = len(workdays)  # 第n个工作日（从1开始计数）
    if n == 0:
        logger.warning(f"特定日期 {specific_date} 及之前无工作日数据")
        return {"date": target_date_str, "page_url": None, "calendar_url": None}

    # 计算特定日期所在的页码
    page_num = (n - 1) // 20 + 1  # 每页20条，第1-20个在第1页，21-40在第2页等

    # 计算总页数（到特定日期为止的总工作日对应的页数）
    total_pages = (n + 19) // 20

    # 确定需要爬取的页码（当前页及前后各一页，处理边界）
    candidate_pages = [page_num - 1, page_num, page_num + 1]
    valid_pages = [p for p in candidate_pages if p >= 1 and p <= total_pages]
    valid_pages = list(set(valid_pages))  # 去重
    valid_pages.sort()

    # 生成需要爬取的列表页URLs
    urls = []
    for p in valid_pages:
        if p == 1:
            urls.append("https://stock.eastmoney.com/a/czpnc.html")
        else:
            urls.append(f"https://stock.eastmoney.com/a/czpnc_{p}.html")
    logger.info(f"将爬取以下列表页: {urls}")

    # 爬取这几页的列表数据，获取日期到详情页链接的映射
    date_and_urls = fetch_em_list_pages(urls)

    # 获取该日期的详情页链接
    page_url = date_and_urls.get(target_date_str)

    # 获取图片链接
    calendar_url = None
    if page_url:
        try:
            calendar_url = get_finance_calendar_image(page_url)
        except Exception as e:
            logger.error(f"获取 {target_date_str} 的日历图片链接失败: {e}")

    return {
        "date": target_date_str,
        "page_url": page_url,
        "calendar_url": calendar_url
    }

get_eastmoney_url()