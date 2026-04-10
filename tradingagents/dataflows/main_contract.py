"""
主力合约换月检测与连续数据复权模块

中国期货主力合约定期切换（每月/每季度），需要处理：
1. 主力合约历史切换记录
2. 检测换月事件
3. 价格复权平滑处理
4. 技术指标连续性处理

复权逻辑：
- 当检测到主力切换时，计算旧主力合约与新主力合约的价格比例
- 将旧主力历史价格按此比例调整，使技术指标连续
- 例如：rb2405 收盘4000，切换到 rb2410 首日收盘4050
- 则复权系数 = 4050/4000 = 1.0125
- 旧主力历史价格 × 1.0125 后与技术指标对接
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, TypedDict
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import akshare as ak


@dataclass
class ContractRollover:
    """换月事件记录"""
    old_contract: str       # 旧主力合约代码
    new_contract: str       # 新主力合约代码
    rollover_date: str       # 换月日期 (yyyy-mm-dd)
    old_last_price: float   # 旧主力最后交易日收盘价
    new_first_price: float # 新主力首日开盘/收盘价
    roll_ratio: float      # 复权系数 (new_price / old_price)


@dataclass
class ContinuousDataResult:
    """连续数据结果"""
    df: pd.DataFrame                    # 复权后的数据
    rollovers: List[ContractRollover]   # 检测到的换月事件列表
    metadata: Dict                       # 元数据（复权系数等）


def _get_all_contracts_for_symbol(symbol: str) -> List[str]:
    """
    获取品种所有历史合约列表。
    
    通过持仓量变化来识别主力合约。
    """
    contracts = []
    
    try:
        # 尝试从交易所获取合约列表
        # SHFE
        try:
            df = ak.futures_contract_info_shfe()
            if df is not None:
                symbol_upper = symbol.upper()
                filtered = df[df['合约代码'].str.upper().str.startswith(symbol_upper)]
                contracts.extend(filtered['合约代码'].tolist())
        except Exception:
            pass
        
        # DCE
        try:
            df = ak.futures_contract_info_dce()
            if df is not None:
                symbol_upper = symbol.upper()
                filtered = df[df['合约代码'].str.upper().str.startswith(symbol_upper)]
                contracts.extend(filtered['合约代码'].tolist())
        except Exception:
            pass
        
        # CZCE
        try:
            df = ak.futures_contract_info_czce()
            if df is not None:
                symbol_upper = symbol.upper()
                filtered = df[df['合约代码'].str.upper().str.startswith(symbol_upper)]
                contracts.extend(filtered['合约代码'].tolist())
        except Exception:
            pass
        
    except Exception:
        pass
    
    # 如果获取失败，生成默认合约列表（最近12个月）
    if not contracts:
        now = datetime.now()
        for i in range(1, 13):
            year = now.year if i <= 12 else now.year + 1
            month = i if i <= 12 else i - 12
            contracts.append(f"{symbol}{year % 100:02d}{month:02d}")
    
    return sorted(set(contracts))


class MainContractTracker:
    """
    主力合约跟踪器
    
    跟踪品种主力合约历史，检测换月事件。
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.lower()
        self._contract_cache: Dict[str, pd.DataFrame] = {}
        self._rollover_history: List[ContractRollover] = []
    
    def get_main_contract_history(
        self,
        start_date: str,
        end_date: str,
        max_contracts: int = 6
    ) -> pd.DataFrame:
        """
        获取主力合约历史列表。
        
        通过跟踪不同到期月份的合约持仓量变化，识别主力合约切换。
        
        Args:
            start_date: 开始日期 (yyyy-mm-dd)
            end_date: 结束日期 (yyyy-mm-dd)
            max_contracts: 最多跟踪的合约数量
            
        Returns:
            DataFrame，包含每日的多个主力候选合约信息
        """
        all_data = []
        contracts_to_check = _get_all_contracts_for_symbol(self.symbol)[:max_contracts]
        
        for contract in contracts_to_check:
            try:
                # 获取该合约的历史日线数据
                df = ak.futures_zh_daily_sina(symbol=contract)
                if df is not None and not df.empty:
                    df = df.copy()
                    df['contract'] = contract
                    
                    # 过滤日期范围
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        start = pd.to_datetime(start_date)
                        end = pd.to_datetime(end_date)
                        df = df[(df['date'] >= start) & (df['date'] <= end)]
                    
                    if not df.empty:
                        all_data.append(df)
            except Exception:
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        # 合并所有合约数据
        combined = pd.concat(all_data, ignore_index=True)
        
        if 'date' in combined.columns:
            combined = combined.sort_values('date')
        
        return combined
    
    def detect_rollovers(
        self,
        start_date: str,
        end_date: str
    ) -> List[ContractRollover]:
        """
        检测主力合约换月事件。
        
        核心思路：
        - 主力合约的标志是持仓量最大
        - 当某合约持仓量从大变小，且另一合约持仓量从小变大时，发生换月
        - 通过追踪持仓量第一名的合约变化来检测换月时点
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            换月事件列表
        """
        history = self.get_main_contract_history(start_date, end_date)
        
        if history.empty:
            return []
        
        # 按日期分组，找到每日持仓量最大的合约
        history = history.sort_values('date')
        
        # 每日持仓量最大的合约（主力合约）
        daily_main = history.loc[history.groupby('date')['hold'].idxmax()]
        daily_main = daily_main.sort_values('date')
        
        # 找到主力合约切换的时点
        rollovers = []
        prev_contract = None
        prev_date = None
        prev_close = 0.0
        
        for idx, row in daily_main.iterrows():
            current_contract = row['contract']
            current_date = row['date']
            current_close = row.get('close', 0)
            
            if prev_contract is not None and current_contract != prev_contract:
                # 主力合约切换
                rollover = ContractRollover(
                    old_contract=prev_contract,
                    new_contract=current_contract,
                    rollover_date=current_date.strftime('%Y-%m-%d') if isinstance(current_date, datetime) else str(current_date),
                    old_last_price=prev_close,
                    new_first_price=current_close,
                    roll_ratio=current_close / prev_close if prev_close > 0 else 1.0
                )
                
                # 过滤掉价格变化过大的异常切换（可能是数据问题）
                if 0.95 < rollover.roll_ratio < 1.05:
                    rollovers.append(rollover)
                    self._rollover_history.append(rollover)
            
            prev_contract = current_contract
            prev_date = current_date
            prev_close = current_close
        
        return rollovers
    
    def get_continuous_price(
        self,
        contract: str,
        start_date: str,
        end_date: str,
        apply_rollover_adjustment: bool = True
    ) -> Tuple[pd.DataFrame, List[ContractRollover]]:
        """
        获取连续价格数据（已复权）。
        
        Args:
            contract: 当前主力合约代码
            start_date: 开始日期
            end_date: 结束日期
            apply_rollover_adjustment: 是否应用换月复权
            
        Returns:
            (复权后的DataFrame, 换月事件列表)
        """
        # 获取当前合约数据
        df = ak.futures_zh_daily_sina(symbol=contract)
        
        if df is None or df.empty:
            return pd.DataFrame(), []
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        df = df.sort_values('date')
        
        rollovers = []
        
        if apply_rollover_adjustment:
            # 检测历史换月事件
            rollovers = self.detect_rollovers(start_date, end_date)
            
            if rollovers:
                # 应用复权系数
                df = self._apply_rollover_adjustment(df, rollovers)
        
        return df, rollovers
    
    def _apply_rollover_adjustment(
        self,
        df: pd.DataFrame,
        rollovers: List[ContractRollover]
    ) -> pd.DataFrame:
        """
        应用换月复权系数到历史数据。
        
        从最近到最远，应用复权系数使价格连续。
        """
        if not rollovers or df.empty:
            return df
        
        df = df.copy()
        df = df.sort_values('date', ascending=False)  # 从新到旧
        
        adjustment_factor = 1.0
        
        for rollover in rollovers:
            rollover_date = pd.to_datetime(rollover.rollover_date)
            
            # 更新累积复权系数
            adjustment_factor *= rollover.roll_ratio
            
            # 对该日期之前的数据应用复权
            mask = df['date'] < rollover_date
            price_cols = ['open', 'high', 'low', 'close', 'settle']
            
            for col in price_cols:
                if col in df.columns:
                    df.loc[mask, col] = df.loc[mask, col] * rollover.roll_ratio
        
        # 记录元数据
        df.attrs['rollover_adjustment'] = adjustment_factor
        df.attrs['rollover_count'] = len(rollovers)
        
        return df.sort_values('date')  # 恢复从旧到新
    
    def check_current_rollover_status(self) -> Optional[ContractRollover]:
        """
        检查当前是否处于换月期间。
        
        Returns:
            如果检测到换月，返回换月信息；否则返回None
        """
        today = datetime.now().strftime('%Y-%m-%d')
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        rollovers = self.detect_rollovers(thirty_days_ago, today)
        
        if rollovers:
            # 返回最近的换月事件
            return rollovers[-1]
        return None
    
    def get_rollover_warning_message(self) -> str:
        """
        生成换月警告消息，用于通知Analyst Agent。
        
        Returns:
            警告消息字符串
        """
        current_rollover = self.check_current_rollover_status()
        
        if current_rollover:
            direction = "向上跳空" if current_rollover.roll_ratio > 1 else "向下跳空"
            return (
                f"【主力换月警告】\n"
                f"检测到主力合约切换：\n"
                f"旧主力: {current_rollover.old_contract}\n"
                f"新主力: {current_rollover.new_contract}\n"
                f"换月日期: {current_rollover.rollover_date}\n"
                f"价格变化: {current_rollover.old_last_price:.2f} → {current_rollover.new_first_price:.2f}\n"
                f"复权系数: {current_rollover.roll_ratio:.4f} ({direction} {abs(current_rollover.roll_ratio - 1) * 100:.2f}%)\n"
                f"注意：跨主力合约的技术指标可能存在断层，建议参考基差结构。"
            )
        
        return ""


class ContinuousFuturesEngine:
    """
    连续期货数据引擎
    
    提供统一的接口获取复权后的连续合约数据。
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol.lower()
        self.tracker = MainContractTracker(symbol)
        self._current_main_contract: Optional[str] = None
    
    def get_continuous_data(
        self,
        start_date: str,
        end_date: str,
        include_rollover_warnings: bool = True
    ) -> ContinuousDataResult:
        """
        获取连续期货数据（自动处理主力换月）。
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            include_rollover_warnings: 是否包含换月警告
            
        Returns:
            ContinuousDataResult对象
        """
        # 获取当前主力合约
        self._current_main_contract = self._get_current_main_contract()
        
        # 获取连续价格数据
        df, rollovers = self.tracker.get_continuous_price(
            self._current_main_contract,
            start_date,
            end_date
        )
        
        metadata = {
            "symbol": self.symbol,
            "current_main_contract": self._current_main_contract,
            "rollover_count": len(rollovers),
            "adjustment_factor": df.attrs.get('rollover_adjustment', 1.0),
            "start_date": start_date,
            "end_date": end_date,
        }
        
        if include_rollover_warnings and rollovers:
            warning_msg = self._generate_rollover_report(rollovers)
            metadata["rollover_warning"] = warning_msg
        
        return ContinuousDataResult(
            df=df,
            rollovers=rollovers,
            metadata=metadata
        )
    
    def _get_current_main_contract(self) -> str:
        """获取当前主力合约"""
        try:
            df = ak.futures_main_sina(symbol=self.symbol)
            if df is not None and not df.empty:
                return df.iloc[0, 0]
        except Exception:
            pass
        return f"{self.symbol}0"
    
    def _generate_rollover_report(self, rollovers: List[ContractRollover]) -> str:
        """生成换月报告"""
        if not rollovers:
            return ""
        
        lines = ["【主力换月历史报告】"]
        
        for i, rollover in enumerate(rollovers, 1):
            direction = "↑" if rollover.roll_ratio > 1 else "↓"
            lines.append(
                f"{i}. {rollover.rollover_date}: "
                f"{rollover.old_contract}({rollover.old_last_price:.2f}) "
                f"{direction} {rollover.new_contract}({rollover.new_first_price:.2f}) "
                f"变动{abs(rollover.roll_ratio - 1) * 100:.2f}%"
            )
        
        lines.append(f"\n提示：历史数据已按最新主力合约进行价格复权处理。")
        
        return "\n".join(lines)
    
    def calculate_technical_indicators_continuous(
        self,
        start_date: str,
        end_date: str,
        indicators: List[str] = None
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        计算连续技术指标（已复权）。
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            indicators: 指标列表 ["sma", "ema", "macd", "boll"]
            
        Returns:
            (包含指标的DataFrame, 换月警告消息)
        """
        if indicators is None:
            indicators = ["sma", "ema", "macd"]
        
        result = self.get_continuous_data(start_date, end_date)
        df = result.df
        
        if df.empty:
            return pd.DataFrame(), None
        
        close_prices = pd.to_numeric(df['close'], errors='coerce')
        
        # SMA
        if "sma" in indicators:
            df['sma_5'] = close_prices.rolling(5).mean()
            df['sma_10'] = close_prices.rolling(10).mean()
            df['sma_20'] = close_prices.rolling(20).mean()
        
        # EMA
        if "ema" in indicators:
            df['ema_12'] = close_prices.ewm(span=12).mean()
            df['ema_26'] = close_prices.ewm(span=26).mean()
        
        # MACD
        if "macd" in indicators:
            ema_12 = close_prices.ewm(span=12).mean()
            ema_26 = close_prices.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_hist'] = histogram
        
        # Bollinger Bands
        if "boll" in indicators:
            sma_20 = close_prices.rolling(20).mean()
            std_20 = close_prices.rolling(20).std()
            df['boll_upper'] = sma_20 + (std_20 * 2)
            df['boll_middle'] = sma_20
            df['boll_lower'] = sma_20 - (std_20 * 2)
        
        warning = result.metadata.get("rollover_warning", "")
        
        return df, warning


def get_rollover_indicator_status(symbol: str) -> Dict:
    """
    获取主力换月状态摘要。
    
    用于快速检查是否需要关注换月影响。
    """
    engine = ContinuousFuturesEngine(symbol)
    current_rollover = engine.tracker.check_current_rollover_status()
    
    return {
        "symbol": symbol,
        "current_main_contract": engine._get_current_main_contract(),
        "has_active_rollover": current_rollover is not None,
        "rollover": {
            "old_contract": current_rollover.old_contract,
            "new_contract": current_rollover.new_contract,
            "rollover_date": current_rollover.rollover_date,
            "roll_ratio": current_rollover.roll_ratio,
        } if current_rollover else None,
    }
