"""akshare-based futures data fetching functions for Chinese futures market."""

from typing import Annotated
from datetime import datetime, timedelta
import pandas as pd
import akshare as ak


def _parse_date(date_str) -> str:
    """Parse date string to yyyy-mm-dd format."""
    if isinstance(date_str, str):
        return date_str
    if hasattr(date_str, 'strftime'):
        return date_str.strftime('%Y-%m-%d')
    return str(date_str)


def _format_date_for_akshare(date_str: str) -> str:
    """Convert yyyy-mm-dd to akshare expected format (yyyymmdd)."""
    return date_str.replace('-', '')


def get_main_contract_code(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb' for rebar, 'hc' for hot rolled coil"],
    exchange: Annotated[str, "exchange code: 'dce' for Dalian, 'czce' for Zhengzhou, 'shfe' for Shanghai, 'cffex' for CFFEX"] = None
) -> str:
    """
    Get the main contract code for a given futures symbol.
    
    Args:
        symbol: Futures symbol code (e.g., 'rb' for rebar, 'hc' for hot rolled coil, 'i' for iron ore)
        exchange: Exchange code (optional, will auto-detect if not provided)
    
    Returns:
        Main contract code string (e.g., 'rb0', 'rb2410', 'hc0')
    """
    try:
        df = ak.get_futures_main_sina(symbol=symbol)
        if df is None or df.empty:
            return f"{symbol}0"
        
        main_contract = df.iloc[0, 0]
        return main_contract
    except Exception as e:
        return f"{symbol}0"


def get_futures_daily_bars(
    symbol: Annotated[str, "main contract code, e.g. 'rb2410' or 'rb0'"],
    start_date: Annotated[str, "start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "end date in yyyy-mm-dd format"],
) -> str:
    """
    Get daily K-line data (OHLCV + open interest) for a futures contract.
    
    Args:
        symbol: Main contract code (e.g., 'rb2410')
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    
    Returns:
        Formatted string containing daily bar data with headers
    """
    try:
        start_str = _format_date_for_akshare(start_date)
        end_str = _format_date_for_akshare(end_date)
        
        df = ak.get_futures_daily_sn(symbol=symbol, start_date=start_str, end_date=end_str)
        
        if df is None or df.empty:
            return f"No data found for {symbol} between {start_date} and {end_date}"
        
        df = df.copy()
        
        if '日期' in df.columns:
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        
        if '收盘' in df.columns and '收盘价' not in df.columns:
            df.rename(columns={'收盘': '收盘价'}, inplace=True)
        
        required_cols = ['日期', '开盘价', '最高价', '最低价', '收盘价', '成交量', '持仓量']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        csv_string = df.to_csv(index=False)
        
        header = f"# Futures daily bars for {symbol} from {start_date} to {end_date}\n"
        header += f"# Total records: {len(df)}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error fetching daily bars for {symbol}: {str(e)}"


def get_futures_ohlc(
    symbol: Annotated[str, "main contract code, e.g. 'rb2410'"],
    start_date: Annotated[str, "start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "end date in yyyy-mm-dd format"],
) -> str:
    """
    Get OHLC (Open-High-Low-Close) data for a futures contract.
    Alias for get_futures_daily_bars with focus on price data.
    
    Args:
        symbol: Main contract code
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    
    Returns:
        Formatted string containing OHLC data
    """
    return get_futures_daily_bars(symbol, start_date, end_date)


def get_futures_basis(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb'"],
    spot_price: Annotated[float, "current spot price of the underlying asset"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Calculate basis data (spot price vs futures price) for a futures symbol.
    
    The basis is calculated as: Basis = Spot Price - Futures Price
    
    Args:
        symbol: Futures symbol code
        spot_price: Current spot price of the underlying asset
        date: Trading date (optional, defaults to today)
    
    Returns:
        Formatted string containing basis data
    """
    try:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        main_contract = get_main_contract_code(symbol)
        
        try:
            start_str = _format_date_for_akshare(date)
            end_str = start_str
            
            df = ak.get_futures_daily_sn(symbol=main_contract, start_date=start_str, end_date=end_str)
            
            futures_price = None
            if df is not None and not df.empty:
                if '收盘价' in df.columns:
                    futures_price = df.iloc[-1]['收盘价']
                elif '收盘' in df.columns:
                    futures_price = df.iloc[-1]['收盘']
        except Exception:
            futures_price = None
        
        if futures_price is None:
            return f"Basis data for {symbol} on {date}: Unable to fetch futures price. Spot price: {spot_price}"
        
        basis = spot_price - futures_price
        basis_percent = (basis / spot_price) * 100 if spot_price != 0 else 0
        
        result = f"""# Basis Data for {symbol} on {date}

Futures Symbol: {symbol}
Main Contract: {main_contract}
Spot Price: {spot_price:.4f}
Futures Price: {futures_price:.4f}
Basis (Spot - Futures): {basis:.4f}
Basis (%): {basis_percent:.4f}%

Interpretation:
- Positive basis (basis > 0): Spot price higher than futures, indicates cash market premium
- Negative basis (basis < 0): Futures price higher than spot, indicates backwardation
- Basis close to zero: Full carry, market in equilibrium
"""
        return result
        
    except Exception as e:
        return f"Error calculating basis for {symbol}: {str(e)}"


def get_futures_inventory(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb' for rebar, 'hc' for hot rolled coil"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Get inventory data for a futures symbol (warehouse receipts, stockpiles).
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional, defaults to most recent available)
    
    Returns:
        Formatted string containing inventory data
    """
    try:
        if date is None:
            date_str = datetime.now().strftime('%Y%m%d')
        else:
            date_str = _format_date_for_akshare(date)
        
        inventory_funcs = {
            'rb': ak.get_futures_inventory_sina,  # Rebar inventory
            'hc': ak.get_futures_inventory_sina,   # Hot rolled coil
            'i': ak.get_futures_inventory_sina,    # Iron ore
        }
        
        if symbol.lower() in inventory_funcs:
            try:
                df = inventory_funcs[symbol.lower()](symbol=symbol.upper())
                
                if df is None or df.empty:
                    return f"No inventory data found for {symbol}"
                
                df = df.copy()
                
                if '日期' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
                
                csv_string = df.to_csv(index=False)
                
                header = f"# Inventory Data for {symbol.upper()}\n"
                header += f"# Date: {date}\n"
                header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                
                return header + csv_string
                
            except Exception:
                pass
        
        futures_inventory_sina = ak.get_futures_inventory_sina(symbol=symbol.upper())
        
        if futures_inventory_sina is None or futures_inventory_sina.empty:
            return f"No specific inventory data available for {symbol}. Please check exchange websites."
        
        futures_inventory_sina = futures_inventory_sina.copy()
        
        if '日期' in futures_inventory_sina.columns:
            futures_inventory_sina['日期'] = pd.to_datetime(futures_inventory_sina['日期']).dt.strftime('%Y-%m-%d')
        
        csv_string = futures_inventory_sina.to_csv(index=False)
        
        header = f"# Futures Inventory Data for {symbol.upper()}\n"
        header += f"# Date: {date}\n"
        header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return header + csv_string
        
    except Exception as e:
        return f"Error fetching inventory for {symbol}: {str(e)}"


def get_futures_position(
    symbol: Annotated[str, "futures symbol code, e.g. 'rb'"],
    date: Annotated[str, "trading date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Get open interest and position data for a futures symbol.
    
    Args:
        symbol: Futures symbol code
        date: Trading date (optional)
    
    Returns:
        Formatted string containing position data
    """
    try:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        main_contract = get_main_contract_code(symbol)
        
        start_str = _format_date_for_akshare(date)
        end_str = start_str
        
        df = ak.get_futures_daily_sn(symbol=main_contract, start_date=start_str, end_date=end_str)
        
        if df is None or df.empty:
            return f"No position data found for {symbol} on {date}"
        
        result = f"""# Position Data for {symbol} on {date}

Main Contract: {main_contract}

Contract Details:
"""
        
        if '持仓量' in df.columns:
            result += f"Open Interest (持仓量): {df.iloc[0]['持仓量']:,}\n"
        if '成交量' in df.columns:
            result += f"Trading Volume (成交量): {df.iloc[0]['成交量']:,}\n"
        
        result += "\nNote: Higher open interest indicates more active market participation."
        
        return result
        
    except Exception as e:
        return f"Error fetching position data for {symbol}: {str(e)}"


def get_futures_historical_indicators(
    symbol: Annotated[str, "main contract code, e.g. 'rb2410'"],
    indicator: Annotated[str, "technical indicator type: 'volume', 'position', 'sma', 'ema', 'macd', 'boll'"],
    start_date: Annotated[str, "start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "end date in yyyy-mm-dd format"],
) -> str:
    """
    Get technical indicators for futures based on daily bars.
    
    Args:
        symbol: Main contract code
        indicator: Type of indicator to calculate
        start_date: Start date
        end_date: End date
    
    Returns:
        Formatted string containing indicator data
    """
    try:
        daily_data = get_futures_daily_bars(symbol, start_date, end_date)
        
        if daily_data.startswith("Error") or daily_data.startswith("No data"):
            return daily_data
        
        lines = daily_data.split('\n')
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith('#'):
                header_end = i + 1
            else:
                break
        
        csv_data = '\n'.join(lines[header_end:])
        from io import StringIO
        df = pd.read_csv(StringIO(csv_data))
        
        result = f"## {indicator.upper()} Analysis for {symbol} from {start_date} to {end_date}\n\n"
        
        if indicator.lower() == 'volume':
            if '成交量' in df.columns:
                result += f"### Trading Volume Analysis\n\n"
                for _, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    vol = row.get('成交量', 0)
                    result += f"{date}: Volume = {vol:,.0f}\n"
        
        elif indicator.lower() == 'position' or indicator.lower() == 'open_interest':
            if '持仓量' in df.columns:
                result += f"### Open Interest Analysis\n\n"
                for _, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    oi = row.get('持仓量', 0)
                    result += f"{date}: Open Interest = {oi:,.0f}\n"
        
        elif indicator.lower() == 'sma':
            if '收盘价' in df.columns:
                close_prices = pd.to_numeric(df['收盘价'], errors='coerce')
                sma_5 = close_prices.rolling(window=5).mean()
                sma_10 = close_prices.rolling(window=10).mean()
                sma_20 = close_prices.rolling(window=20).mean()
                
                result += f"### Simple Moving Averages\n\n"
                result += "| Date       | Close    | SMA(5)   | SMA(10)  | SMA(20)  |\n"
                result += "|------------|----------|----------|----------|----------|\n"
                for i, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    close = row.get('收盘价', 0)
                    s5 = sma_5.iloc[i] if pd.notna(sma_5.iloc[i]) else 0
                    s10 = sma_10.iloc[i] if pd.notna(sma_10.iloc[i]) else 0
                    s20 = sma_20.iloc[i] if pd.notna(sma_20.iloc[i]) else 0
                    result += f"| {date} | {close:8.2f} | {s5:8.2f} | {s10:8.2f} | {s20:8.2f} |\n"
        
        elif indicator.lower() == 'ema':
            if '收盘价' in df.columns:
                close_prices = pd.to_numeric(df['收盘价'], errors='coerce')
                ema_12 = close_prices.ewm(span=12, adjust=False).mean()
                ema_26 = close_prices.ewm(span=26, adjust=False).mean()
                
                result += f"### Exponential Moving Averages\n\n"
                result += "| Date       | Close    | EMA(12)  | EMA(26)  |\n"
                result += "|------------|----------|----------|----------|\n"
                for i, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    close = row.get('收盘价', 0)
                    e12 = ema_12.iloc[i] if pd.notna(ema_12.iloc[i]) else 0
                    e26 = ema_26.iloc[i] if pd.notna(ema_26.iloc[i]) else 0
                    result += f"| {date} | {close:8.2f} | {e12:8.2f} | {e26:8.2f} |\n"
        
        elif indicator.lower() == 'macd':
            if '收盘价' in df.columns:
                close_prices = pd.to_numeric(df['收盘价'], errors='coerce')
                ema_12 = close_prices.ewm(span=12, adjust=False).mean()
                ema_26 = close_prices.ewm(span=26, adjust=False).mean()
                macd_line = ema_12 - ema_26
                signal_line = macd_line.ewm(span=9, adjust=False).mean()
                histogram = macd_line - signal_line
                
                result += f"### MACD Analysis\n\n"
                result += "| Date       | MACD     | Signal   | Histogram |\n"
                result += "|------------|----------|----------|----------|\n"
                for i, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    m = macd_line.iloc[i] if pd.notna(macd_line.iloc[i]) else 0
                    s = signal_line.iloc[i] if pd.notna(signal_line.iloc[i]) else 0
                    h = histogram.iloc[i] if pd.notna(histogram.iloc[i]) else 0
                    result += f"| {date} | {m:8.4f} | {s:8.4f} | {h:8.4f} |\n"
        
        elif indicator.lower() == 'boll' or indicator.lower() == 'bollinger':
            if '收盘价' in df.columns:
                close_prices = pd.to_numeric(df['收盘价'], errors='coerce')
                sma_20 = close_prices.rolling(window=20).mean()
                std_20 = close_prices.rolling(window=20).std()
                upper_band = sma_20 + (std_20 * 2)
                lower_band = sma_20 - (std_20 * 2)
                
                result += f"### Bollinger Bands\n\n"
                result += "| Date       | Lower    | SMA(20)  | Upper    |\n"
                result += "|------------|----------|----------|----------|\n"
                for i, row in df.iterrows():
                    date = row.get('日期', 'N/A')
                    s = sma_20.iloc[i] if pd.notna(sma_20.iloc[i]) else 0
                    u = upper_band.iloc[i] if pd.notna(upper_band.iloc[i]) else 0
                    l = lower_band.iloc[i] if pd.notna(lower_band.iloc[i]) else 0
                    result += f"| {date} | {l:8.2f} | {s:8.2f} | {u:8.2f} |\n"
        
        else:
            result += f"Indicator '{indicator}' not supported. Available: volume, position, sma, ema, macd, boll\n"
        
        result += "\n"
        result += f"### Indicator Descriptions\n\n"
        result += "- **SMA**: Simple Moving Average, trend indicator\n"
        result += "- **EMA**: Exponential Moving Average, responsive to price changes\n"
        result += "- **MACD**: Moving Average Convergence Divergence, momentum indicator\n"
        result += "- **Bollinger Bands**: Volatility bands around a moving average\n"
        
        return result
        
    except Exception as e:
        return f"Error calculating indicator {indicator} for {symbol}: {str(e)}"


def get_market_news(look_back_hours: int = 24) -> str:
    """
    获取市场7x24小时实时快讯。
    数据来源：东方财富华尔街见闻快讯。

    Args:
        look_back_hours: 回溯小时数，默认24小时

    Returns:
        格式化的时间线式新闻文本
    """
    try:
        df = ak.news_em_news()
        
        if df is None or df.empty:
            return "暂无市场快讯数据"
        
        df = df.copy()
        
        news_items = []
        for idx, row in df.head(50).iterrows():
            timestamp = row.get('发布时间', row.get('时间', 'N/A'))
            source = row.get('来源', row.get('source', '华尔街见闻'))
            title = row.get('标题', row.get('title', ''))
            content = row.get('内容', row.get('content', ''))
            
            if pd.isna(title) or not title:
                continue
            
            news_items.append(f"[{timestamp}] {source}\n标题：{title}")
            if pd.notna(content) and content:
                news_items.append(f"内容：{content[:200]}...")
            news_items.append("")
        
        if not news_items:
            return "暂无市场快讯数据"
        
        result = "# 市场7x24小时实时快讯\n"
        result += f"# 数据来源：华尔街见闻\n"
        result += f"# 获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"# 共获取 {len(news_items)//2} 条快讯\n\n"
        result += "---\n\n".join(news_items)
        
        return result
        
    except Exception as e:
        return f"获取市场快讯失败：{str(e)}"


def get_sina_futures_news(symbol: str) -> str:
    """
    获取新浪财经期货品种相关快讯。

    Args:
        symbol: 期货品种代码 (如 'rb', 'hc', 'IF')

    Returns:
        格式化品种相关新闻文本
    """
    try:
        try:
            df_sina = ak.get_article_news_xq(symbol=symbol.upper())
            if df_sina is not None and not df_sina.empty:
                news_data = df_sina
            else:
                news_data = None
        except Exception:
            news_data = None
        
        if news_data is None or news_data.empty:
            general_news = get_market_news(look_back_hours=24)
            return f"# {symbol.upper()} 相关快讯\n\n未找到品种专属快讯，以下是市场概览：\n\n{general_news}"
        
        news_data = news_data.copy()
        
        news_items = []
        for idx, row in news_data.head(20).iterrows():
            timestamp = row.get('发布时间', row.get('时间', 'N/A'))
            title = row.get('标题', row.get('title', ''))
            content = row.get('内容', row.get('content', ''))
            
            if pd.isna(title) or not title:
                continue
            
            news_items.append(f"[{timestamp}]\n标题：{title}")
            if pd.notna(content) and content:
                news_items.append(f"摘要：{content[:300]}")
            news_items.append("")
        
        if not news_items:
            return f"# {symbol.upper()} 相关快讯\n\n暂无相关新闻数据"
        
        result = f"# {symbol.upper()} 相关快讯\n"
        result += f"# 数据来源：新浪财经\n"
        result += f"# 获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"# 共获取 {len(news_items)//2} 条\n\n"
        result += "---\n\n".join(news_items)
        
        return result
        
    except Exception as e:
        return f"获取 {symbol} 新闻失败：{str(e)}"


def get_futures_research_reports(symbol: str, limit: int = 10) -> str:
    """
    获取东方财富期货品种最新研报摘要。

    Args:
        symbol: 期货品种代码 (如 'rb', 'IF')
        limit: 返回研报数量，默认10篇

    Returns:
        格式化研报摘要文本
    """
    try:
        try:
            df = ak.report_em_research_report(symbol=symbol.upper(), symbol_name="")
            if df is None or df.empty:
                df = ak.report_em_research_report(symbol="", symbol_name=symbol.upper())
                if df is None or df.empty:
                    return f"# {symbol.upper()} 研报摘要\n\n暂无{symbol.upper()}相关研报数据"
        except Exception:
            df = None
        
        if df is None or df.empty:
            return f"# {symbol.upper()} 研报摘要\n\n暂无{symbol.upper()}相关研报数据"
        
        df = df.head(limit)
        df = df.copy()
        
        report_items = []
        for idx, row in df.iterrows():
            title = row.get('研报标题', row.get('标题', 'N/A'))
            author = row.get('分析师', row.get('作者', 'N/A'))
            org = row.get('机构', row.get('券商', 'N/A'))
            date = row.get('公布日期', row.get('日期', row.get('时间', 'N/A')))
            rating = row.get('评级', row.get('投资评级', 'N/A'))
            summary = row.get('概要', row.get('摘要', row.get('内容', '')))
            
            if pd.isna(title) or not title:
                continue
            
            report_items.append(f"【研报标题】{title}")
            report_items.append(f"【分析师】{author} @ {org}")
            report_items.append(f"【评级】{rating}")
            report_items.append(f"【日期】{date}")
            if pd.notna(summary) and summary:
                report_items.append(f"【核心观点】{summary[:500]}")
            report_items.append("")
        
        if not report_items:
            return f"# {symbol.upper()} 研报摘要\n\n暂无{symbol.upper()}相关研报数据"
        
        result = f"# {symbol.upper()} 研报摘要\n"
        result += f"# 数据来源：东方财富\n"
        result += f"# 获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"# 共获取 {len(report_items)//5} 篇研报\n\n"
        result += "=" * 60 + "\n\n"
        result += "\n\n".join(report_items)
        
        result += "\n\n" + "=" * 60 + "\n"
        result += "【研报评级说明】\n"
        result += "- 强烈推荐：预期涨幅>30%\n"
        result += "- 买入/推荐：预期涨幅>15%\n"
        result += "- 增持/中性：预期涨幅0-15%\n"
        result += "- 减持/卖出：预期涨幅<0%\n"
        
        return result
        
    except Exception as e:
        return f"获取 {symbol} 研报失败：{str(e)}"


def get_macro_news(look_back_days: int = 7) -> str:
    """
    获取宏观新闻和经济数据预告。
    
    Args:
        look_back_days: 回溯天数

    Returns:
        格式化宏观新闻文本
    """
    try:
        try:
            df = ak.macro_china_news()
            if df is None or df.empty:
                news_df = None
            else:
                news_df = df
        except Exception:
            news_df = None
        
        if news_df is None or news_df.empty:
            return "# 宏观新闻摘要\n\n暂无宏观新闻数据，请关注华尔街见闻快讯"
        
        news_df = news_df.head(30)
        news_df = news_df.copy()
        
        news_items = []
        for idx, row in news_df.iterrows():
            title = row.get('标题', 'N/A')
            date = row.get('发布时间', row.get('时间', 'N/A'))
            content = row.get('内容', row.get('内容', ''))[:200]
            
            if pd.isna(title) or not title:
                continue
            
            news_items.append(f"[{date}] {title}")
            if pd.notna(content):
                news_items.append(f"{content}...")
            news_items.append("")
        
        if not news_items:
            return "# 宏观新闻摘要\n\n暂无宏观新闻数据"
        
        result = "# 宏观新闻摘要\n"
        result += f"# 数据来源：东方财富\n"
        result += f"# 获取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"# 共获取 {len(news_items)//2} 条\n\n"
        result += "---\n\n".join(news_items)
        
        return result
        
    except Exception as e:
        return f"获取宏观新闻失败：{str(e)}"
