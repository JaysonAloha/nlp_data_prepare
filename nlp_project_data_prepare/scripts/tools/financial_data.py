import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from scripts.logging_config import setup_logger

logger=setup_logger("financial_data")

def get_financial_metrics(symbol: str):
    """获取财务报表-利润表数据"""
    logger.info(f"Getting financial metrics for {symbol}")
    try:
        #获取实时行情数据
        logger.info("Fetching real-time data . . .")
        realtime_data=ak.stock_zh_a_spot_em()  #获取当前所有中国 A 股股票的实时行情快照
        if realtime_data is None or realtime_data.empty:
            logger.warning("No real-time data quotes available")
            return [{}]

        stock_data=realtime_data[realtime_data['代码'] == symbol]
        if stock_data.empty:
            logger.warning(f"No real-time data quotes available for {symbol}")
            return [{}]

        stock_data=stock_data.iloc[0]
        logger.info("Real-time data fetched successfully")

        #获取新浪财务指标
        logger.info("Fetching financial indicators . . .")
        current_year=datetime.now().year
        financial_data=ak.stock_financial_analysis_indicator(symbol=symbol,start_year=str(current_year-1))
        if financial_data is None or financial_data.empty:
            logger.warning(f"No real-time data quotes available for {symbol}")
            return [{}]

        financial_data['日期']=pd.to_datetime(financial_data['日期'])
        financial_data=financial_data.sort_values('日期',ascending=False)
        latest_financial_data=financial_data.iloc[0] if not financial_data.empty else pd.Series()
        logger.info(f"Financial data fetched ({latest_financial_data.get('日期')})")
        logger.info(f"Latest data date: {latest_financial_data.get('日期')}")

        #获取利润表的数据
        logger.info("Fetching income statement...")
        try:
            income_statement=ak.stock_financial_report_sina(stock=f"sh{symbol}",symbol="利润表")
            if not income_statement.empty:
                latest_income=income_statement.iloc[0]
                logger.info(f"Latest income statement fetched successfully")
            else:
                logger.warning(f"Failed to fetch income statement for {symbol}")
                logger.error("No income statement fetched successfully")
                latest_income=pd.Series()
        except Exception as e:
            logger.warning("Failed to get income statement")
            logger.error(f"Error getting income statement: {e}")
            latest_income=pd.Series()

        #构建完整的指标数据
        logger.info("Indicators building . . .")
        try:
            def convert_percentage_float(value: float):
                """将百分比值转换为小数"""
                try:
                    return float(value)/100.0 if value is not None else 0.0
                except Exception as e:
                    return 0.0


            all_metrics={
                #市场数据
                "market_cap" : float(stock_data.get("总市值",0)),
                "float_market_cap": float(stock_data.get("流通市值", 0)),

                # 盈利数据
                "revenue": float(latest_income.get("营业总收入", 0)),
                "net_income": float(latest_income.get("净利润", 0)),
                "return_on_equity": convert_percentage_float(latest_financial_data.get("净资产收益率(%)", 0)),
                "net_margin": convert_percentage_float(latest_financial_data.get("销售净利率(%)", 0)),
                "operating_margin": convert_percentage_float(latest_financial_data.get("营业利润率(%)", 0)),

                # 增长指标
                "revenue_growth": convert_percentage_float(latest_financial_data.get("主营业务收入增长率(%)", 0)),
                "earnings_growth": convert_percentage_float(latest_financial_data.get("净利润增长率(%)", 0)),
                "book_value_growth": convert_percentage_float(latest_financial_data.get("净资产增长率(%)", 0)),

                # 财务健康指标
                "current_ratio": float(latest_financial_data.get("流动比率", 0)),
                "debt_to_equity": convert_percentage_float(latest_financial_data.get("资产负债率(%)", 0)),
                "free_cash_flow_per_share": float(latest_financial_data.get("每股经营性现金流(元)", 0)),
                "earnings_per_share": float(latest_financial_data.get("加权每股收益(元)", 0)),

                # 估值比率
                "pe_ratio": float(stock_data.get("市盈率-动态", 0)),
                "price_to_book": float(stock_data.get("市净率", 0)),
                "price_to_sales": float(stock_data.get("总市值", 0)) / float(
                    latest_income.get("营业总收入", 1)) if float(latest_income.get("营业总收入", 0)) > 0 else 0,
            }

            #只返回agent需要的指标
            agent_metrics={
                # 盈利能力指标
                "return_on_equity": all_metrics["return_on_equity"],
                "net_margin": all_metrics["net_margin"],
                "operating_margin": all_metrics["operating_margin"],

                # 增长指标
                "revenue_growth": all_metrics["revenue_growth"],
                "earnings_growth": all_metrics["earnings_growth"],
                "book_value_growth": all_metrics["book_value_growth"],

                # 财务健康指标
                "current_ratio": all_metrics["current_ratio"],
                "debt_to_equity": all_metrics["debt_to_equity"],
                "free_cash_flow_per_share": all_metrics["free_cash_flow_per_share"],
                "earnings_per_share": all_metrics["earnings_per_share"],

                # 估值比率
                "pe_ratio": all_metrics["pe_ratio"],
                "price_to_book": all_metrics["price_to_book"],
                "price_to_sales": all_metrics["price_to_sales"],
            }

            logger.info("Indicators built successfully")

            logger.debug("\nAll indicators fetched:")
            for key,value in all_metrics.items():
                logger.debug(f"{key}: {value}")

            logger.debug("\nIndicators passed to agent")
            for key,value in agent_metrics.items():
                logger.debug(f"{key}: {value}")

            return [agent_metrics]

        except Exception as e:
            logger.error(f"Error building indicators: {e}")
            return [{}]

    except Exception as e:
        logger.error(f"Error fetching financial indicators: {e}")
        return [{}]


def get_financial_statements(symbol: str):
    """获取财务报表-资产负债表数据"""
    logger.info(f"Getting financial statements for {symbol}")
    try:
        #获取资产负债表
        logger.info("Fetching balance sheet . . .")
        try:
            balance_sheet=ak.stock_financial_report_sina(stock=f"sh{symbol}",symbol="资产负债表")
            if not balance_sheet.empty:
                latest_balance=balance_sheet.iloc[0]
                previous_balance=balance_sheet.iloc[1] if len(balance_sheet)>1 else balance_sheet.iloc[0]
                logger.info("Balance sheet fetched successfully")
            else:
                logger.warning("Failed to get balance sheet")
                logger.error("No balance sheet available")
                latest_balance=pd.Series()
                previous_balance=pd.Series()
        except Exception as e:
            logger.warning(f"Error fetching balance sheet")
            logger.error(f"Error fetching balance sheet: {e}")
            latest_balance=pd.Series()
            previous_balance=pd.Series()

        #获取利润表数据
        logger.info("Fetching income statement . . .")
        try:
            income_sheet = ak.stock_financial_report_sina(stock=f"sh{symbol}", symbol="利润表")
            if not income_sheet.empty:
                latest_income = income_sheet.iloc[0]
                previous_income = income_sheet.iloc[1] if len(income_sheet) > 1 else income_sheet.iloc[0]
                logger.info("Income sheet fetched successfully")
            else:
                logger.warning("Failed to get income sheet")
                logger.error("No income sheet available")
                latest_income = pd.Series()
                previous_income = pd.Series()
        except Exception as e:
            logger.warning(f"Error fetching income sheet")
            logger.error(f"Error fetching income sheet: {e}")
            latest_income=pd.Series()
            previous_income=pd.Series()

        # 获取现金流量表数据
        logger.info("Fetching cash flow sheet...")
        try:
            cash_flow = ak.stock_financial_report_sina(stock=f"sh{symbol}", symbol="现金流量表")
            if not cash_flow.empty:
                latest_cash_flow = cash_flow.iloc[0]
                previous_cash_flow = cash_flow.iloc[1] if len(cash_flow) > 1 else cash_flow.iloc[0]
                logger.info("Cash flow statement fetched successfully")
            else:
                logger.warning("Failed to get cash flow sheet")
                logger.error("No cash flow data found")
                latest_cash_flow = pd.Series()
                previous_cash_flow = pd.Series()
        except Exception as e:
            logger.warning("Failed fetching cash flow sheet")
            logger.error(f"Error fetching cash flow sheet: {e}")
            latest_cash_flow = pd.Series()
            previous_cash_flow = pd.Series()

        #构建财务数据
        financial_periods=[]
        try:
            #最新一期财务数据
            current_record={
                #利润表
                "net_income":float(latest_income.get("净利润",0)),
                "operating_revenue": float(latest_income.get("营业总收入", 0)),
                "operating_profit": float(latest_income.get("营业利润", 0)),

                # 从资产负债表计算营运资金
                "working_capital": float(latest_balance.get("流动资产合计", 0)) - float(
                    latest_balance.get("流动负债合计", 0)),

                # 从现金流量表获取
                "depreciation_and_amortization": float(latest_cash_flow.get("固定资产折旧、油气资产折耗、生产性生物资产折旧", 0)),
                "capital_expenditure": abs(float(latest_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0))),
                "free_cash_flow": float(latest_cash_flow.get("经营活动产生的现金流量净额", 0)) - abs(float(latest_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0)))
            }
            financial_periods.append(current_record)
            logger.info("Latest financial period fetched successfully")

            #处理上一期数据
            previous_record={
                "net_income": float(previous_income.get("净利润", 0)),
                "operating_revenue": float(previous_income.get("营业总收入", 0)),
                "operating_profit": float(previous_income.get("营业利润", 0)),
                "working_capital": float(previous_balance.get("流动资产合计", 0)) - float(previous_balance.get("流动负债合计", 0)),
                "depreciation_and_amortization": float(previous_cash_flow.get("固定资产折旧、油气资产折耗、生产性生物资产折旧", 0)),
                "capital_expenditure": abs(float(previous_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0))),
                "free_cash_flow": float(previous_cash_flow.get("经营活动产生的现金流量净额", 0)) - abs(float(previous_cash_flow.get("购建固定资产、无形资产和其他长期资产支付的现金", 0)))
            }
            financial_periods.append(previous_record)
            logger.info("Previous financial period fetched successfully")

        except Exception as e:
            logger.error(f"Error processing financial data: {e}")
            default_item={
                "net_income": 0,
                "operating_revenue": 0,
                "operating_profit": 0,
                "working_capital": 0,
                "depreciation_and_amortization": 0,
                "capital_expenditure": 0,
                "free_cash_flow": 0
            }
            financial_periods=[default_item, default_item]

        return financial_periods

    except Exception as e:
        logger.error(f"Error fetching financial statements: {e}")
        default_item={
            "net_income": 0,
            "operating_revenue": 0,
            "operating_profit": 0,
            "working_capital": 0,
            "depreciation_and_amortization": 0,
            "capital_expenditure": 0,
            "free_cash_flow": 0
        }
        return [default_item,default_item]

def get_market_data(symbol: str):
    """获取实时市场数据"""
    try:
        realtime_data=ak.stock_zh_a_spot_em()
        stock_data=realtime_data[realtime_data['代码'] == symbol].iloc[0]

        return {
            "market_cap": float(stock_data.get("总市值", 0)),
            "volume": float(stock_data.get("成交量", 0)),
            # A股实时交易数据没有平均成交量，暂用当日成交量
            "average_volume": float(stock_data.get("成交量", 0)),
            "fifty_two_week_high": float(stock_data.get("52周最高", 0)),
            "fifty_two_week_low": float(stock_data.get("52周最低", 0))
        }
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return {}

def get_price_history(symbol: str, start_date: str = None, end_date: str = None, adjust: str = "qfq"):
    """
     Args:
        symbol: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD，如果为None则默认获取过去一年的数据
        end_date: 结束日期，格式：YYYY-MM-DD，如果为None则使用昨天作为结束日期
        adjust: 复权类型，可选值：
               - "": 不复权
               - "qfq": 前复权（默认）
               - "hfq": 后复权

    Returns:
        包含以下列的DataFrame：
        - date: 日期
        - open: 开盘价
        - high: 最高价
        - low: 最低价
        - close: 收盘价
        - volume: 成交量（手）
        - amount: 成交额（元）
        - amplitude: 振幅（%）
        - pct_change: 涨跌幅（%）
        - change_amount: 涨跌额（元）
        - turnover: 换手率（%）

        技术指标：
        - momentum_1m: 1个月动量
        - momentum_3m: 3个月动量
        - momentum_6m: 6个月动量
        - volume_momentum: 成交量动量
        - historical_volatility: 历史波动率
        - volatility_regime: 波动率区间
        - volatility_z_score: 波动率Z分数
        - atr_ratio: 真实波动幅度比率
        - hurst_exponent: 赫斯特指数
        - skewness: 偏度
        - kurtosis: 峰度
    """
    try:
        current_date=datetime.now()
        yesterday=current_date-timedelta(days=1)

        if not end_date:
            end_date=yesterday
        else:
            end_date=datetime.strptime(end_date, "%Y-%m-%d")
            if end_date > yesterday:
                end_date=yesterday

        if not start_date:
            start_date=end_date-timedelta(days=365)
        else:
            start_date=datetime.strptime(start_date, "%Y-%m-%d")

        logger.info(f"Fetching price history for {symbol} from {start_date} to {end_date}")

        def process_data(start_date, end_date):
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=adjust,
            )

            if df is None or df.empty:
                return pd.DataFrame()

            df=df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "pct_change",
                "涨跌额": "change_amount",
                "换手率": "turnover",
            })

            df["date"]=pd.to_datetime(df["date"])
            return df

        df=process_data(start_date, end_date)

        if df is None or df.empty:
            logger.warning(f"No price history data found for {symbol}")
            return pd.DataFrame()

        min_days_required=120
        if len(df)<min_days_required:
            logger.warning(f"Insufficient data ({len(df)} days) for all technical indicators")
            logger.info("Trying to fetch more data . . .")

            start_date=end_date-timedelta(days=730)
            df=process_data(start_date, end_date)

            if len(df)<min_days_required:
                logger.warning(f"Even with extended time range, insufficient data ({len(df)} days)")

        #动量指标
        df["momentum_1m"] = df["close"].pct_change(periods=20)  # 20个交易日约等于1个月
        df["momentum_3m"] = df["close"].pct_change(periods=60)  # 60个交易日约等于3个月
        df["momentum_6m"] = df["close"].pct_change(periods=120)  # 120个交易日约等于6个月

        # 计算成交量动量（相对于20日平均成交量的变化）
        df["volume_ma20"] = df["volume"].rolling(window=20).mean()
        df["volume_momentum"] = df["volume"] / df["volume_ma20"]

        # 计算波动率指标
        # 1. 历史波动率 (20日)
        returns = df["close"].pct_change()
        df["historical_volatility"] = returns.rolling(window=20).std() * np.sqrt(252)  # 年化

        # 2. 波动率区间 (相对于过去120天的波动率的位置)
        volatility_120d = returns.rolling(window=120).std() * np.sqrt(252)
        vol_min = volatility_120d.rolling(window=120).min()
        vol_max = volatility_120d.rolling(window=120).max()
        vol_range = vol_max - vol_min
        df["volatility_regime"] = np.where(
            vol_range > 0,
            (df["historical_volatility"] - vol_min) / vol_range,
            0  # 当范围为0时返回0
        )

        # 3. 波动率Z分数
        vol_mean = df["historical_volatility"].rolling(window=120).mean()
        vol_std = df["historical_volatility"].rolling(window=120).std()
        df["volatility_z_score"] = (df["historical_volatility"] - vol_mean) / vol_std

        # 4. ATR比率
        tr = pd.DataFrame()
        tr["h-l"] = df["high"] - df["low"]
        tr["h-pc"] = abs(df["high"] - df["close"].shift(1))
        tr["l-pc"] = abs(df["low"] - df["close"].shift(1))
        tr["tr"] = tr[["h-l", "h-pc", "l-pc"]].max(axis=1)
        df["atr"] = tr["tr"].rolling(window=14).mean()
        df["atr_ratio"] = df["atr"] / df["close"]

        # 统计套利指标
        # 5. 赫斯特指数 (使用过去120天的数据)
        # Hurst=0.5 表示序列随机（无记忆）；Hurst>0.5 表示序列有 “趋势记忆”（如上涨后倾向继续上涨）；Hurst<0.5 表示序列有 “反转记忆”（如上涨后倾向回调）
        def calculate_hurst(series):
            try:
                series=series.dropna()
                if len(series)<30:
                    return np.nan

                #计算对数收益率
                log_returns= np.log(series/series.shift(1)).dropna()
                if len(log_returns)<30:
                    return np.nan

                #样本量较小，使用2-10的lag
                lags=range(2,min(11,len(log_returns)//4))
                # 计算每个lag的标准差
                tau = []
                for lag in lags:
                    # 计算滚动标准差
                    std = log_returns.rolling(window=lag).std().dropna()
                    if len(std) > 0:
                        tau.append(np.mean(std))

                # 基本的数值检查
                if len(tau) < 3:  # 进一步降低最小要求
                    return np.nan

                # 使用对数回归
                lags_log = np.log(list(lags))
                tau_log = np.log(tau)

                # 计算回归系数
                reg = np.polyfit(lags_log, tau_log, 1)
                hurst = reg[0] / 2.0

                # 只保留基本的数值检查
                if np.isnan(hurst) or np.isinf(hurst):
                    return np.nan

                return hurst

            except Exception as e:
                return np.nan

        # 使用对数收益率计算Hurst指数
        log_returns = np.log(df["close"] / df["close"].shift(1))
        df["hurst_exponent"] = log_returns.rolling(
            window=120,
            min_periods=60  # 要求至少60个数据点
        ).apply(calculate_hurst)

        # 2. 偏度 (20日)
        df["skewness"] = returns.rolling(window=20).skew()

        # 3. 峰度 (20日)
        df["kurtosis"] = returns.rolling(window=20).kurt()

        # 按日期升序排序
        df = df.sort_values("date")

        # 重置索引
        df = df.reset_index(drop=True)

        logger.info(f"Successfully fetched price history data ({len(df)} records)")

        #检查NaN情况
        nan_columns=df.isna().sum()
        if nan_columns.any():
            logger.warning("Warning: The following indicators contain NaN values:")
            for col, nan_count in nan_columns[nan_columns>0].items():
                logger.warning(f"\n{col}: {nan_count} records")

        return df

    except Exception as e:
        logger.error(f"Failed to fetch price history data ({e})")
        return pd.DataFrame()

def prices_to_df(prices):
    try:
        df=pd.DataFrame(prices)
        #标准化列名
        column_mapping = {
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "涨跌幅": "percent_change",
            "涨跌额": "change_amount",
            "换手率": "turnover_rate"
        }
        #重命名列。并保留原中文列
        for cn,en in column_mapping.items():
            if cn in df.columns:
                df[en]=df[cn]
        #确保必要的列存在
        required_columns = ["open","close","high","low","volume"]
        for col in required_columns:
            if col not in df.columns:
                df[col]=0.0   #不存在用0补缺

        return df
    except Exception as e:
        logger.error(f"Error converting price data ({str(e)})")
        return pd.DataFrame(columns=["open","close","high","low","volume"])

def get_price_data(symbol:str, start_date:str, end_date:str):
    """获取股票价格数据

       Args:
           symbol: 股票代码
           start_date: 开始日期，格式：YYYY-MM-DD
           end_date: 结束日期，格式：YYYY-MM-DD

       Returns:
           包含价格数据的DataFrame
       """
    return get_price_history(symbol, start_date, end_date)