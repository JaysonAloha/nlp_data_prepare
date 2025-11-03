# nlp_data_prepare
该项目是一个用于 NLP（自然语言处理）项目的数据准备工具集，主要专注于获取和处理金融领域相关数据，包括股票价格数据、财经新闻、东方财富早报等，为后续的 NLP 分析任务提供数据支持。

## 项目结构
```
nlp_project_data_prepare/
└── scripts/
    ├── tools/
    │   ├── eastmoney_breakfast.py  # 东方财富早报数据获取
    │   ├── test.py                 # 网页渲染与解析工具（依赖Playwright）
    │   ├── data_analyzer.py        # 股票数据技术指标分析
    │   ├── web_search.py           # 网页搜索功能（基于Playwright）
    │   ├── financial_data.py       # 股票价格历史数据获取与处理
    │   ├── news_crawler.py         # 股票相关新闻爬取
    │   └── logging_config.py       # 日志配置工具
    └── logs/                       # 日志文件存储目录（自动生成）
```

## 功能说明
1.东方财富早报获取（eastmoney_breakfast.py）  
- 爬取东方财富网早报内容及对应日期的链接  
- 自动处理工作日判断（排除周末和法定节假日）  
- 支持指定日期范围的数据获取  
  
2.股票数据技术指标分析（data_analyzer.py）  
- 计算常见技术指标（MA、MACD、RSI、布林带等）  
- 分析成交量、价格动量、波动率等特征  
- 生成结构化分析结果并保存为 CSV 文件  
  
3.网页搜索功能（web_search.py）  
- 基于 Playwright 实现模拟浏览器搜索  
- 支持自定义搜索选项（结果数量、超时时间等）  
- 反爬虫处理（浏览器指纹模拟、状态保存）  
  
4.股票价格数据获取（financial_data.py）  
- 获取股票历史价格数据（开盘价、收盘价、成交量等）  
- 支持复权类型选择（前复权、后复权、不复权）  
- 计算动量指标、波动率、赫斯特指数等金融特征  
  
5.股票新闻爬取（news_crawler.py）  
- 支持通过 Google 搜索或 AKShare 获取股票相关新闻  
- 自动过滤无效新闻（招聘、广告、开户等）  
- 实现新闻数据缓存机制，避免重复爬取  
  
6.网页渲染与解析（test.py）  
- 使用 Playwright 渲染动态网页内容  
- 解析网页中的新闻列表及日期信息  
- 自动处理浏览器依赖安装  
  
## 安装说明
### 前置依赖
Python 3.8+
依赖库：pandas, requests, beautifulsoup4, playwright, akshare, chinese-calendar, numpy

## 安装步骤
### 克隆项目代码
```
git clone <项目仓库地址>
cd nlp_project_data_prepare
```
### 安装依赖包
```
pip install pandas requests beautifulsoup4 playwright akshare chinese-calendar numpy
#安装 Playwright 浏览器（首次使用时需要）

python -m playwright install chromium
```
## 使用示例
1.分析股票数据
```
from scripts.tools.data_analyzer import analyze_stock_data
from datetime import datetime, timedelta


# 分析贵州茅台（600519）近一年数据
symbol = "600519"
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
analyze_stock_data(symbol, start_date, end_date)
```

2.获取股票新闻
```
from scripts.tools.news_crawler import get_stock_news

# 获取贵州茅台（600519）的最新10条新闻
news_list = get_stock_news("600519", max_news=10)
print(f"获取到 {len(news_list)} 条新闻")
```
3.获取股票历史价格数据
```
from scripts.tools.financial_data import get_price_history

# 获取贵州茅台（600519）的价格历史数据
df = get_price_history("600519")
print(f"获取到 {len(df)} 条价格记录")
```
4.. 获取东方财富早报链接
```
from scripts.tools.eastmoney_breakfast import get_em_url_page

# 获取早报链接并保存到JSON文件
url_dict = get_em_url_page()
print(f"获取到 {len(url_dict)} 条早报链接")
```

