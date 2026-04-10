#!/usr/bin/env python3
"""
End-to-End Testing Script for TradingAgents LangGraph Pipeline

This script tests the complete flow for Chinese futures:
Data Acquisition -> Fundamentals Analysis -> Technical Analysis -> 
Macro News Analysis -> Risk Assessment -> Final Trading Decision

Hardcoded futures contract: 螺纹钢 (rb) as the main contract
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Iterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

# Initialize rich console
console = Console()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.dataflows.akshare_futures import (
    get_main_contract_code,
    get_futures_daily_bars,
    get_futures_historical_indicators,
    get_futures_basis,
    get_futures_inventory,
    get_futures_position,
)


# ============================================================================
# Configuration
# ============================================================================

FUTURES_SYMBOL = "rb"
TRADE_DATE = datetime.now().strftime("%Y-%m-%d")
POSITION_DIRECTION = "Long"

RECENT_TRADE_DATE = "2024-11-15"

SELECTED_ANALYSTS = ["market", "fundamentals", "news"]


# ============================================================================
# Rich-styled Output Helpers
# ============================================================================

def print_header(text: str, style: str = "bold blue"):
    """Print a section header with rich styling."""
    console.print(Panel(f"[bold]{text}[/bold]", style="blue", expand=False))


def print_agent_header(agent_name: str, status: str = "running"):
    """Print agent processing header."""
    status_color = "green" if status == "running" else "yellow" if status == "waiting" else "red"
    console.print(f"\n{'='*80}")
    console.print(f"[{status_color}] {'●' if status == 'running' else '○'} {agent_name}[/{status_color}]")
    console.print(f"{'='*80}")


def print_data_block(title: str, content: str, max_lines: int = 50):
    """Print data block with rich formatting."""
    lines = content.split('\n')
    if len(lines) > max_lines:
        content = '\n'.join(lines[:max_lines]) + f"\n... [dim]({len(lines) - max_lines} more lines)[/dim]"
    
    console.print(Panel(
        content[:2000] if len(content) > 2000 else content,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
        expand=False
    ))


def print_json_decision(decision_data: Dict[str, Any]):
    """Print final decision as formatted JSON."""
    console.print("\n")
    console.print(Panel(
        "[bold green]FINAL TRADING DECISION[/bold green]",
        style="green bold",
        expand=False
    ))
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", width=25)
    table.add_column("Value", style="white")
    
    for key, value in decision_data.items():
        if isinstance(value, str) and len(value) > 100:
            table.add_row(key, value[:100] + "...")
        else:
            table.add_row(key, str(value))
    
    console.print(table)


def print_error_with_context(error: Exception, context: str):
    """Print error with context."""
    console.print(f"\n[bold red]ERROR in {context}:[/bold red]")
    console.print(f"[red]{str(error)[:200]}[/red]")


# ============================================================================
# Data Fetching Functions for Testing
# ============================================================================

def fetch_market_data(symbol: str, main_contract: str, trade_date: str) -> Dict[str, str]:
    """Fetch all market data for testing without LLM."""
    result = {}
    
    console.print(f"\n[cyan]Fetching market data for {symbol} ({main_contract})...[/cyan]")
    
    # Get daily bars
    start_date = (datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        bars = get_futures_daily_bars(main_contract, start_date, trade_date)
        result['daily_bars'] = bars
        console.print(f"[green]✓[/green] Daily bars fetched ({len(bars)} chars)")
    except Exception as e:
        result['daily_bars'] = f"Error: {e}"
        console.print(f"[red]✗[/red] Daily bars error: {e}")
    
    # Get technical indicators
    try:
        indicators = get_futures_historical_indicators(main_contract, "sma", start_date, trade_date)
        result['indicators'] = indicators
        console.print(f"[green]✓[/green] Technical indicators fetched ({len(indicators)} chars)")
    except Exception as e:
        result['indicators'] = f"Error: {e}"
        console.print(f"[red]✗[/red] Technical indicators error: {e}")
    
    return result


def fetch_fundamentals_data(symbol: str, trade_date: str) -> Dict[str, str]:
    """Fetch all fundamental data for testing without LLM."""
    result = {}
    
    console.print(f"\n[cyan]Fetching fundamental data for {symbol}...[/cyan]")
    
    # Get basis data
    try:
        basis = get_futures_basis(symbol, spot_price=3500.0, date=trade_date)
        result['basis'] = basis
        console.print(f"[green]✓[/green] Basis data fetched ({len(basis)} chars)")
    except Exception as e:
        result['basis'] = f"Error: {e}"
        console.print(f"[red]✗[/red] Basis data error: {e}")
    
    # Get inventory data
    try:
        inventory = get_futures_inventory(symbol, date=trade_date)
        result['inventory'] = inventory
        console.print(f"[green]✓[/green] Inventory data fetched ({len(inventory)} chars)")
    except Exception as e:
        result['inventory'] = f"Error: {e}"
        console.print(f"[red]✗[/red] Inventory data error: {e}")
    
    # Get position data
    try:
        position = get_futures_position(symbol, date=trade_date)
        result['position'] = position
        console.print(f"[green]✓[/green] Position data fetched ({len(position)} chars)")
    except Exception as e:
        result['position'] = f"Error: {e}"
        console.print(f"[red]✗[/red] Position data error: {e}")
    
    return result


# ============================================================================
# E2E Test Runner
# ============================================================================

class E2ETestRunner:
    """Runner for end-to-end trading agent testing."""
    
    def __init__(self, futures_symbol: str = "rb", trade_date: str = None, 
                 position_direction: str = "Long", debug: bool = True,
                 skip_llm: bool = False):
        self.futures_symbol = futures_symbol
        self.trade_date = trade_date or RECENT_TRADE_DATE
        self.position_direction = position_direction
        self.debug = debug
        self.skip_llm = skip_llm
        self.console = console
        
        self.main_contract = None
        
        self.state_history = []
        
    def get_main_contract_info(self) -> Dict[str, str]:
        """Get main contract information for the symbol."""
        try:
            main_contract_code = get_main_contract_code(self.futures_symbol)
            self.main_contract = main_contract_code
            
            return {
                "symbol": self.futures_symbol,
                "main_contract": main_contract_code,
                "display_name": "螺纹钢" if self.futures_symbol.lower() == "rb" else self.futures_symbol.upper(),
                "exchange": "SHFE"
            }
        except Exception as e:
            print_error_with_context(e, "get_main_contract_info")
            return {
                "symbol": self.futures_symbol,
                "main_contract": f"{self.futures_symbol}0",
                "display_name": self.futures_symbol.upper(),
                "exchange": "Unknown"
            }
    
    def setup_graph(self) -> TradingAgentsGraph:
        """Initialize the trading agents graph with custom configuration."""
        
        config = DEFAULT_CONFIG.copy()
        config.update({
            "debug": False,
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
        })
        
        try:
            graph = TradingAgentsGraph(
                selected_analysts=SELECTED_ANALYSTS,
                debug=False,
                config=config,
                callbacks=None
            )
            return graph
        except Exception as e:
            print_error_with_context(e, "setup_graph")
            raise
    
    def run_data_fetching_demo(self):
        """Demonstrate data fetching without LLM."""
        
        console.print(Panel.fit(
            "[bold white on blue] TradingAgents E2E Data Fetching Demo [/bold white on blue]\n"
            f"Futures Symbol: {self.futures_symbol.upper()}\n"
            f"Trade Date: {self.trade_date}\n"
            f"Position Direction: {self.position_direction}\n"
            "Mode: Data Fetching Only (LLM calls skipped)",
            border_style="blue"
        ))
        
        print_header("Step 1: 获取主力合约信息")
        contract_info = self.get_main_contract_info()
        print_json_decision(contract_info)
        
        print_header("Step 2: 获取市场数据 (技术分析)")
        market_data = fetch_market_data(
            self.futures_symbol, 
            contract_info['main_contract'],
            self.trade_date
        )
        
        print_header("Step 3: 获取基本面数据")
        fundamentals_data = fetch_fundamentals_data(
            self.futures_symbol,
            self.trade_date
        )
        
        print_header("Step 4: 数据汇总")
        
        # Display all fetched data
        for title, content in market_data.items():
            print_data_block(title.upper(), content, max_lines=80)
        
        for title, content in fundamentals_data.items():
            print_data_block(title.upper(), content, max_lines=80)
        
        return {
            "contract_info": contract_info,
            "market_data": market_data,
            "fundamentals_data": fundamentals_data
        }
    
    def run_with_streaming(self, graph: TradingAgentsGraph, 
                           ticker: str, trade_date: str, 
                           position_direction: str) -> tuple:
        """Run the graph with streaming to capture intermediate states."""
        
        from tradingagents.graph.propagation import Propagator
        
        propagator = Propagator(max_recur_limit=100)
        init_agent_state = propagator.create_initial_state(
            ticker, trade_date, position_direction
        )
        graph_args = propagator.get_graph_args()
        
        all_states = []
        all_messages = []
        
        console.print(f"\n[cyan]Starting stream execution...[/cyan]\n")
        
        for chunk in graph.graph.stream(init_agent_state, **graph_args):
            all_states.append(chunk)
            
            for key, value in chunk.items():
                if key == "messages" and value:
                    last_msg = value[-1]
                    all_messages.append(last_msg)
                    
                    if hasattr(last_msg, 'name') and last_msg.name:
                        agent_name = last_msg.name
                    else:
                        agent_name = "Message"
                    
                    content = ""
                    if hasattr(last_msg, 'content') and last_msg.content:
                        content = last_msg.content
                    
                    if content and len(content) > 0:
                        if self.debug:
                            print_agent_header(agent_name, "running")
                            preview = content[:300] + "..." if len(content) > 300 else content
                            console.print(Panel(
                                preview,
                                title=f"[bold cyan]{agent_name}[/bold cyan]",
                                border_style="cyan",
                                expand=False
                            ))
            
            console.print("[dim]...[/dim]", end="")
        
        console.print("\n")
        
        final_state = all_states[-1] if all_states else {}
        
        if isinstance(final_state, dict) and "final_trade_decision" not in final_state:
            for state in reversed(all_states):
                if isinstance(state, dict) and "final_trade_decision" in state:
                    final_state = state
                    break
        
        return final_state, all_states
    
    def run(self):
        """Execute the full E2E test pipeline."""
        
        if self.skip_llm:
            return self.run_data_fetching_demo()
        
        start_time = time.time()
        
        console.print("\n")
        console.print(Panel.fit(
            "[bold white on blue] TradingAgents E2E Test Pipeline [/bold white on blue]\n"
            f"Futures Symbol: {self.futures_symbol.upper()}\n"
            f"Trade Date: {self.trade_date}\n"
            f"Position Direction: {self.position_direction}\n"
            f"Analysts: {', '.join(SELECTED_ANALYSTS)}",
            border_style="blue"
        ))
        
        print_header("Step 1: 获取主力合约信息")
        contract_info = self.get_main_contract_info()
        print_json_decision(contract_info)
        
        print_header("Step 2: 初始化 LangGraph")
        try:
            graph = self.setup_graph()
            console.print("[green]✓[/green] Graph initialized successfully")
        except Exception as e:
            print_error_with_context(e, "Graph Initialization")
            raise
        
        print_header("Step 3: 执行 Agent 流程")
        
        ticker = f"{contract_info['exchange']}:{contract_info['main_contract']}"
        if self.position_direction == "Short":
            ticker += "|SHORT"
        
        console.print(f"\n[cyan]Running analysis for:[/cyan] {ticker}")
        console.print(f"[cyan]Trade date:[/cyan] {self.trade_date}\n")
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(
                    "[cyan]Running trading agents pipeline...", 
                    total=None
                )
                
                final_state, all_states = self.run_with_streaming(
                    graph, ticker, self.trade_date, self.position_direction
                )
                
                processed_signal = graph.process_signal(
                    final_state.get("final_trade_decision", "")
                )
                
                progress.update(task, completed=True)
            
            print_header("Step 4: 分析结果")
            self._display_results(final_state, processed_signal, all_states)
            
        except Exception as e:
            print_error_with_context(e, "Graph Propagation")
            console.print("\n[yellow]Attempting to display partial results...[/yellow]")
            if 'all_states' in dir() and all_states:
                self._display_results(all_states[-1] if all_states else {}, "ERROR", all_states)
        
        elapsed_time = time.time() - start_time
        console.print(f"\n[bold]Total execution time:[/bold] {elapsed_time:.2f} seconds")
        
        return final_state if 'final_state' in dir() else None
    
    def _display_results(self, final_state: AgentState, processed_signal: str, 
                        all_states: list = None):
        """Display the results from the graph execution."""
        
        if not final_state:
            console.print("[red]No final state available[/red]")
            return
        
        results_table = Table(title="Agent Execution Summary", show_header=True)
        results_table.add_column("Agent Stage", style="cyan bold", width=25)
        results_table.add_column("Status", style="green", width=10)
        results_table.add_column("Content Preview", style="white")
        
        stages = [
            ("market_report", "Market Analyst"),
            ("fundamentals_report", "Fundamentals Analyst"),
            ("news_report", "News Analyst"),
            ("sentiment_report", "Sentiment Analyst"),
        ]
        
        for state_key, agent_name in stages:
            content = final_state.get(state_key, "")
            if content:
                preview = content[:80].replace('\n', ' ') + "..." if len(content) > 80 else content
                results_table.add_row(agent_name, "[green]✓[/green]", preview)
            else:
                results_table.add_row(agent_name, "[yellow]empty[/yellow]", "")
        
        console.print(results_table)
        
        console.print("\n")
        invest_debate = final_state.get("investment_debate_state", {})
        debate_table = Table(title="Investment Debate State", show_header=True)
        debate_table.add_column("Field", style="cyan", width=25)
        debate_table.add_column("Value", style="white")
        
        for key in ["bull_history", "bear_history", "judge_decision"]:
            value = invest_debate.get(key, "")[:200] if invest_debate.get(key) else "N/A"
            debate_table.add_row(key, value)
        
        console.print(debate_table)
        
        console.print("\n")
        risk_debate = final_state.get("risk_debate_state", {})
        risk_table = Table(title="Risk Debate State", show_header=True)
        risk_table.add_column("Field", style="cyan", width=25)
        risk_table.add_column("Value", style="white")
        
        for key in ["aggressive_history", "conservative_history", "neutral_history", "judge_decision"]:
            value = risk_debate.get(key, "")[:200] if risk_debate.get(key) else "N/A"
            risk_table.add_row(key, value)
        
        console.print(risk_table)
        
        console.print("\n")
        final_decision = final_state.get("final_trade_decision", "N/A")
        decision_table = Table(title="Final Trading Decision", show_header=True)
        decision_table.add_column("Field", style="cyan", width=25)
        decision_table.add_column("Value", style="green bold")
        
        decision_table.add_row("Signal", processed_signal if processed_signal else "N/A")
        decision_table.add_row("Decision", final_decision[:500] if final_decision else "N/A")
        
        console.print(decision_table)
        
        print_header("Complete State JSON")
        try:
            state_json = json.dumps(dict(final_state), indent=2, ensure_ascii=False, default=str)
            if len(state_json) > 3000:
                state_json = state_json[:3000] + "\n\n... [truncated]"
            console.print(Syntax(state_json, "json", theme="monokai", line_numbers=False))
        except Exception as e:
            console.print(f"[red]Error serializing state: {e}[/red]")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for E2E testing."""
    console.print("\n")
    
    import argparse
    parser = argparse.ArgumentParser(description="TradingAgents E2E Test")
    parser.add_argument("--symbol", "-s", default=FUTURES_SYMBOL, 
                        help=f"Futures symbol (default: {FUTURES_SYMBOL})")
    parser.add_argument("--date", "-d", default=TRADE_DATE,
                        help=f"Trade date YYYY-MM-DD (default: {TRADE_DATE})")
    parser.add_argument("--direction", default=POSITION_DIRECTION,
                        choices=["Long", "Short"],
                        help="Position direction")
    parser.add_argument("--no-debug", action="store_true",
                        help="Disable debug mode")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip LLM calls, only fetch data")
    
    args = parser.parse_args()
    
    trade_date = args.date
    if trade_date == TRADE_DATE and datetime.now().hour < 17:
        trade_date = RECENT_TRADE_DATE
    
    runner = E2ETestRunner(
        futures_symbol=args.symbol,
        trade_date=trade_date,
        position_direction=args.direction,
        debug=not args.no_debug,
        skip_llm=args.skip_llm
    )
    
    try:
        result = runner.run()
        
        if result:
            console.print("\n[bold green]✓ E2E Test Completed Successfully[/bold green]")
            return 0
        else:
            console.print("\n[bold yellow]⚠ E2E Test Completed with Errors[/bold yellow]")
            return 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]E2E Test Interrupted by User[/yellow]")
        return 130
    except Exception as e:
        print_error_with_context(e, "main")
        return 1


if __name__ == "__main__":
    sys.exit(main())
