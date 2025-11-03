import os
import json
import pandas as pd
from urllib.parse import urlparse
from datetime import date,datetime, timedelta
from chinese_calendar import is_workday
from scripts.logging_config import setup_logger
import requests
from bs4 import BeautifulSoup
import re
import sys
import subprocess
from test import main



logger=setup_logger("eastmoney_breakfast")


def get_previous_workday(date: datetime = None) -> datetime:
    """获取指定日期的上一个工作日（排除周末和法定节假日）"""
    if date is None:
        date = datetime.now()

    current_date = date - timedelta(days=1)
    while not is_workday(current_date):
        current_date -= timedelta(days=1)
    return current_date



def get_eastmoney_url(end_date: datetime = None) :
    if end_date is None:
        end_date = date.today()
    start_date=datetime(year=2022,month=11,day=2)
    workday_count= sum(1 for d in pd.date_range(start=start_date, end=end_date) if is_workday(d.date()))
    urls=["https://stock.eastmoney.com/a/czpnc.html"]
    for i in range(2,workday_count//20+1):
        url="https://stock.eastmoney.com/a/czpnc"+"_"+str(i)+".html"
        urls.append(url)
    return urls

def get_em_url_page():
    urls=get_eastmoney_url()
    urls=urls[:2]
    date_and_urls={}
    for url in urls:
        html=main(url)
        date_and_urls.update(html)
    print(len(date_and_urls))
    with open("eastmoney_breakfast_urls.json","w",encoding="utf-8") as f:
        json.dump(date_and_urls,f)
    return date_and_urls


def download_content_from_url(url):




def get_eastmoney_breakfast(end_date: datetime = None) :
    first_date=datetime(year=2022,month=10,day=11)
    if end_date is None:
        end_date = datetime.now()
        latest_workday = get_previous_workday(end_date)
    if end_date < first_date:
        # 显式格式化日期，只保留年月日
        logger.warning(f"No eastmoney breakfast for {date.strftime('%Y-%m-%d')}")
        logger.info(f"Fecthing eastmoney breakfast for {first_date.strftime('%Y-%m-%d')}")
        latest_workday=first_date

    try:
        url_dict=get_em_url_page()
        try:
            url_end_date=url_dict.get("latest_workday",None)
            if url_end_date is None:
                get_eastmoney_url()



if __name__ == '__main__':
    get_em_url_page()