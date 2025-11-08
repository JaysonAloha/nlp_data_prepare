import os
import re
import sys
import json
from asyncio import timeout
from datetime import datetime, timedelta
import time
import pandas as pd
from urllib.parse import urlparse

# 导入新的搜索模块
try:
    from cache.web_search import google_search_sync, SearchOptions
except ImportError:
    print("警告: 无法导入新的搜索模块，将回退到 akshare")
    google_search_sync = None
    SearchOptions = None

# 保留 akshare 作为备用
try:
    import akshare as ak
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("警告: akshare 不可用")
    ak = None

def build_search_query(ticker:str,date:str=None):
    """
    构建针对股票新闻的 Google 搜索查询

    Args:
        ticker: 股票代码，如 "300059"
        date: 截止日期，格式 "YYYY-MM-DD"

    Returns:
        构建好的搜索查询字符串
    """
    #基础查询
    base_query=f"{ticker} 股票 新闻 财经 股市"

    #如果有时间限制，要求指定日期之前
    if date:
        try:
            end_date=datetime.strptime(date,"%Y-%m-%d")
            start_date=end_date-timedelta(days=7)
            base_query+=f"after:{start_date.strftime('%Y-%m-%d')} before {end_date.strftime('%Y-%m-%d')}"
        except ValueError:
            print(f"日期格式错误: {date}，忽略时间限制")

    news_sites=[
        "site:sina.com.cn",
        "site:163.com",
        "site:eastmoney.com",
        "site:cnstock.com",
        "site:hexun.com"
    ]

    query=f"{base_query} ({' OR '.join(news_sites)})"
    return query

def extract_domain(url:str):
    try:
        parsed=urlparse(url)
        return parsed.netloc
    except:
        return "Unknown source"

def convert_search_results_to_news(search_results,ticker:str) :
    news_list=[]
    for result in search_results:
        if any(keyword in result.title.lower() for keyword in ["招聘","求职","广告","登录","注册","开户"]):
            continue

        # 尝试从snippet中提取时间信息
        publish_time = None
        if result.snippet:
            # 查找常见的时间模式
            time_patterns = [
                r'(\d{1,2}天前)',
                r'(\d{1,2}小时前)',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{2}-\d{2})'
            ]

            for pattern in time_patterns:
                match = re.search(pattern, result.snippet)
                if match:
                    time_str = match.group(1)
                    try:
                        # 处理相对时间
                        if '天前' in time_str:
                            days = int(time_str.replace('天前', ''))
                            publish_date = datetime.now() - timedelta(days=days)
                            publish_time = publish_date.strftime(
                                '%Y-%m-%d %H:%M:%S')
                        elif '小时前' in time_str:
                            hours = int(time_str.replace('小时前', ''))
                            publish_date = datetime.now() - timedelta(hours=hours)
                            publish_time = publish_date.strftime(
                                '%Y-%m-%d %H:%M:%S')
                        # YYYY-MM-DD格式
                        elif '-' in time_str and len(time_str) == 10:
                            publish_time = f"{time_str} 00:00:00"
                        break
                    except:
                        continue

        news_item = {
            "title": result.title,
            "content": result.snippet or result.title,
            "source": extract_domain(result.link),
            "url": result.link,
            "keyword": ticker,
            "search_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 搜索时间
        }

        # 只有当能提取到发布时间时才添加，否则不包含这个字段
        if publish_time:
            news_item["publish_time"] = publish_time

        news_list.append(news_item)

        return news_list


def get_stock_news_via_akshare(symbol: str, max_news: int = 10) -> list:
    """使用 akshare 获取股票新闻的原始方法"""
    if ak is None:
        return []

    try:
        # 获取新闻列表
        news_df = ak.stock_news_em(symbol=symbol)
        if news_df is None or len(news_df) == 0:
            print(f"未获取到{symbol}的新闻数据")
            return []

        print(f"成功获取到{len(news_df)}条新闻")

        # 实际可获取的新闻数量
        available_news_count = len(news_df)
        if available_news_count < max_news:
            print(f"警告：实际可获取的新闻数量({available_news_count})少于请求的数量({max_news})")
            max_news = available_news_count

        # 获取指定条数的新闻（考虑到可能有些新闻内容为空，多获取50%）
        news_list = []
        for _, row in news_df.head(int(max_news * 1.5)).iterrows():
            try:
                # 获取新闻内容
                content = row["新闻内容"] if "新闻内容" in row and not pd.isna(
                    row["新闻内容"]) else ""
                if not content:
                    content = row["新闻标题"]

                # 只去除首尾空白字符
                content = content.strip()
                if len(content) < 10:  # 内容太短的跳过
                    continue

                # 获取关键词
                keyword = row["关键词"] if "关键词" in row and not pd.isna(
                    row["关键词"]) else ""

                # 添加新闻
                news_item = {
                    "title": row["新闻标题"].strip(),
                    "content": content,
                    "publish_time": row["发布时间"],
                    "source": row["文章来源"].strip(),
                    "url": row["新闻链接"].strip(),
                    "keyword": keyword.strip()
                }
                news_list.append(news_item)
                print(f"成功添加新闻: {news_item['title']}")

            except Exception as e:
                print(f"处理单条新闻时出错: {e}")
                continue

        # 按发布时间排序
        news_list.sort(key=lambda x: x["publish_time"], reverse=True)

        # 只保留指定条数的有效新闻
        return news_list[:max_news]

    except Exception as e:
        print(f"akshare 获取新闻数据时出错: {e}")
        return []

def get_stock_news(ticker, max_news: int = 10, date: str = None) -> list:
    max_news = min(max_news,100)

    cache_date = date if date else datetime.now().strftime('%Y-%m-%d')

    #新闻文件保存路径
    news_dir=os.path.join("cache", "news", "stock_news",ticker)
    print(f"新闻保存目录为：{news_dir}")

    try:
        os.makedirs(news_dir, exist_ok=True)
        print(f"成功创建或确认目录存在: {news_dir}")
    except Exception as e:
        print(f"创建目录失败: {e}")
        return []

    news_file_path = os.path.join(news_dir, f"{ticker}_news_{cache_date}.json")
    print(f"新闻文件保存路径为{news_file_path}")

    #检查缓存
    cached_news = []
    cache_valid = False

    if os.path.exists(news_file_path):
        try:
            file_mtime = os.path.getmtime(news_file_path)

            #当日的缓存仅在当日有效，历史日期的缓存始终有效
            if date:
                cache_valid=True
            else:
                cache_date_obj=datetime.fromtimestamp(file_mtime).date()
                today=datetime.now().date()
                cache_valid= cache_date_obj==today

            if cache_valid:
                with open(news_file_path, "r", encoding="utf-8") as f:
                    data=json.load(f)
                    cached_news=data.get("news",[])

                    if len(cached_news) >= max_news:
                        print( f"使用缓存的新闻数据: {news_file_path} (缓存数量: {len(cached_news)})")
                        return cached_news[:max_news]
                    else:
                        print(f"缓存的新闻数量({len(cached_news)})不足，需要获取更多新闻")
            else:
                print(f"缓存文件已过期，将重新获取新闻")

        except Exception as e:
            print(f"读取缓存文件失败{e}")
            cached_news=[]
    print(f"开始获取{ticker}的新闻")

    #计算需要新获取新闻的数量
    more_news_num= max_news - len(cached_news)
    fetch_count= max(more_news_num, max_news)

    #优先使用google
    new_news_list=[]
    if google_search_sync and SearchOptions:
        try:
            print("使用Google搜索新闻")

            search_query = build_search_query(ticker,date)
            print(f"搜索查询： {search_query}")

            search_options= SearchOptions(
                limit=fetch_count*2,
                timeout=30000,
                locale="zh-CN",
            )

            search_response=google_search_sync(search_query,search_options)

            if search_response.results:
                new_news_list=convert_search_results_to_news(search_response.results,ticker)
                print(f"通过 Google 搜索成功获取到{len(new_news_list)}条新闻")
            else:
                print("Google 搜索未返回有效结果，尝试回退到 akshare")

        except Exception as e:
            print(f"Google 搜索获取新闻时出错: {e}，回退到 akshare")

    if not new_news_list:
        print("使用akshare获取新闻……")
        new_news_list = get_stock_news_via_akshare(ticker, fetch_count)

    if cached_news and new_news_list:
        exsting_titles= {news["title"] for news in cached_news}
        unique_new_news = [news for news in new_news_list if news["title"] not in exsting_titles]

        combined_news=cached_news+unique_new_news
        print(f"合并缓存新闻({len(cached_news)}条)和新获取新闻({len(unique_new_news)}条)，总计{len(combined_news)}条")

    else:
        combined_news=new_news_list or cached_news

    #按发布时间排序
    try:
        combined_news.sort(key=lambda x: x.get("publish_time",""), reverse=True)
    except:
        pass

    final_news_list=combined_news[:max_news]

    if new_news_list or not cache_valid:
        try:
            data_to_save={
                "date":cache_date,
                "method": "online_search" if new_news_list and google_search_sync else "akshare",
                "query": build_search_query(ticker,date) if new_news_list and google_search_sync else None,
                "news": combined_news,
                "cached_count": len(cached_news),
                "news_count": len(new_news_list),
                "total_count": len(combined_news),
                "last_updated": datetime.now().isoformat(),
            }

            with open(news_file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            print(f"成功保存{len(combined_news)}条新闻到文件: {news_file_path}")
        except Exception as e:
            print(f"保存新闻至文件出错：{e}")
    return final_news_list

ticker="000300"
get_stock_news(ticker, max_news=10, date=None)