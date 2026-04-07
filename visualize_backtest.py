"""Backtest results visualization and metrics calculation."""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial"]
plt.rcParams["axes.unicode_minus"] = False


def load_results(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_dataframe(results: dict) -> pd.DataFrame:
    """Build a daily DataFrame from backtest results."""
    rows = []
    for day in results["daily_log"]:
        rows.append(
            {
                "date": pd.Timestamp(day["date"]),
                "open": day["open"],
                "high": day["high"],
                "low": day["low"],
                "close": day["close"],
                "total_value": day["total_value"],
                "position_pct": day["position"]["current_position_pct"],
                "shares_traded": (
                    day["order"]["shares_traded"] if "order" in day else 0
                ),
                "trade_cost": abs(day["order"]["cost"]) if "order" in day else 0,
                "triggered": day.get("trigger", {}).get("reason"),
            }
        )
    df = pd.DataFrame(rows).set_index("date")
    return df


def compute_metrics(df: pd.DataFrame, initial_capital: float, risk_free_rate: float = 0.04) -> dict:
    """Compute performance metrics for both strategy and buy-and-hold."""
    n_days = len(df)
    annualize_factor = 252 / n_days

    # --- Strategy ---
    strat_daily_returns = df["total_value"].pct_change().dropna()
    strat_total_return = (df["total_value"].iloc[-1] / initial_capital) - 1
    strat_cagr = (1 + strat_total_return) ** annualize_factor - 1
    strat_vol = strat_daily_returns.std() * np.sqrt(252)
    strat_sharpe = (strat_cagr - risk_free_rate) / strat_vol if strat_vol > 0 else 0

    # Max drawdown
    strat_cummax = df["total_value"].cummax()
    strat_drawdown = (df["total_value"] - strat_cummax) / strat_cummax
    strat_max_dd = strat_drawdown.min()

    # Turnover: sum of |shares_traded * price| / avg total_value
    trade_volume = (df["shares_traded"].abs() * df["close"]).sum()
    avg_value = df["total_value"].mean()
    turnover = trade_volume / avg_value if avg_value > 0 else 0

    # Transaction costs (assume 0.1% per trade value as estimate)
    cost_rate = 0.001
    total_tx_cost = trade_volume * cost_rate

    # --- Buy and Hold ---
    bh_values = initial_capital * (df["close"] / df["close"].iloc[0])
    bh_daily_returns = bh_values.pct_change().dropna()
    bh_total_return = (bh_values.iloc[-1] / initial_capital) - 1
    bh_cagr = (1 + bh_total_return) ** annualize_factor - 1
    bh_vol = bh_daily_returns.std() * np.sqrt(252)
    bh_sharpe = (bh_cagr - risk_free_rate) / bh_vol if bh_vol > 0 else 0
    bh_cummax = bh_values.cummax()
    bh_drawdown = (bh_values - bh_cummax) / bh_cummax
    bh_max_dd = bh_drawdown.min()

    return {
        "strategy": {
            "total_return": strat_total_return,
            "cagr": strat_cagr,
            "volatility": strat_vol,
            "sharpe": strat_sharpe,
            "max_drawdown": strat_max_dd,
            "turnover": turnover,
            "tx_cost_estimate": total_tx_cost,
        },
        "buy_hold": {
            "total_return": bh_total_return,
            "cagr": bh_cagr,
            "volatility": bh_vol,
            "sharpe": bh_sharpe,
            "max_drawdown": bh_max_dd,
        },
        "series": {
            "strat_values": df["total_value"],
            "bh_values": bh_values,
            "strat_drawdown": strat_drawdown,
            "bh_drawdown": bh_drawdown,
        },
    }


def plot_results(df: pd.DataFrame, metrics: dict, ticker: str, save_path: str):
    """Create a 4-panel visualization."""
    series = metrics["series"]
    strat = metrics["strategy"]
    bh = metrics["buy_hold"]

    fig, axes = plt.subplots(4, 1, figsize=(14, 16), sharex=True)
    fig.suptitle(f"{ticker} Backtest Results", fontsize=16, fontweight="bold", y=0.98)

    dates = df.index

    # --- Panel 1: Equity Curve ---
    ax1 = axes[0]
    ax1.plot(dates, series["strat_values"], label="Strategy", color="#2196F3", linewidth=1.5)
    ax1.plot(dates, series["bh_values"], label="Buy & Hold", color="#9E9E9E", linewidth=1.2, linestyle="--")
    ax1.fill_between(dates, series["strat_values"], series["bh_values"],
                     where=series["strat_values"] >= series["bh_values"],
                     alpha=0.15, color="#4CAF50")
    ax1.fill_between(dates, series["strat_values"], series["bh_values"],
                     where=series["strat_values"] < series["bh_values"],
                     alpha=0.15, color="#F44336")
    ax1.set_ylabel("Portfolio Value ($)")
    ax1.legend(loc="upper left")
    ax1.set_title("Equity Curve")
    ax1.grid(True, alpha=0.3)

    # --- Panel 2: Drawdown ---
    ax2 = axes[1]
    ax2.fill_between(dates, series["strat_drawdown"] * 100, 0, alpha=0.4, color="#F44336", label="Strategy DD")
    ax2.plot(dates, series["bh_drawdown"] * 100, color="#9E9E9E", linewidth=1, linestyle="--", label="B&H DD")
    ax2.set_ylabel("Drawdown (%)")
    ax2.legend(loc="lower left")
    ax2.set_title("Drawdown")
    ax2.grid(True, alpha=0.3)

    # --- Panel 3: Position % ---
    ax3 = axes[2]
    ax3.fill_between(dates, df["position_pct"], 0, alpha=0.5, color="#FF9800")
    ax3.set_ylabel("Position (%)")
    ax3.set_title("Position Allocation")
    ax3.set_ylim(0, 105)
    ax3.grid(True, alpha=0.3)

    # Mark triggers
    triggers = df[df["triggered"].notna()]
    for _, row in triggers.iterrows():
        color = "#F44336" if row["triggered"] == "stop_loss" else "#4CAF50"
        marker = "v" if row["triggered"] == "stop_loss" else "^"
        ax3.scatter(row.name, row["position_pct"], color=color, marker=marker, s=80, zorder=5)

    # --- Panel 4: Daily Trades ---
    ax4 = axes[3]
    buys = df[df["shares_traded"] > 0]
    sells = df[df["shares_traded"] < 0]
    ax4.bar(buys.index, buys["shares_traded"], color="#4CAF50", alpha=0.7, label="Buy", width=1.5)
    ax4.bar(sells.index, sells["shares_traded"], color="#F44336", alpha=0.7, label="Sell", width=1.5)
    ax4.set_ylabel("Shares Traded")
    ax4.set_title("Trading Activity")
    ax4.legend(loc="upper left")
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax4.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha="right")

    # --- Metrics Table ---
    metrics_text = (
        f"{'':─<50}\n"
        f"{'Metric':<28} {'Strategy':>12} {'Buy & Hold':>12}\n"
        f"{'':─<50}\n"
        f"{'Total Return':<28} {strat['total_return']:>11.2%} {bh['total_return']:>11.2%}\n"
        f"{'Annualized Return (CAGR)':<28} {strat['cagr']:>11.2%} {bh['cagr']:>11.2%}\n"
        f"{'Volatility':<28} {strat['volatility']:>11.2%} {bh['volatility']:>11.2%}\n"
        f"{'Sharpe Ratio':<28} {strat['sharpe']:>11.2f} {bh['sharpe']:>11.2f}\n"
        f"{'Max Drawdown':<28} {strat['max_drawdown']:>11.2%} {bh['max_drawdown']:>11.2%}\n"
        f"{'Turnover':<28} {strat['turnover']:>11.2f}x\n"
        f"{'Est. Tx Cost (0.1%)':<28} ${strat['tx_cost_estimate']:>10,.2f}\n"
    )
    fig.text(0.12, -0.02, metrics_text, fontsize=10, fontfamily="monospace",
             verticalalignment="top",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#F5F5F5", edgecolor="#BDBDBD"))

    plt.tight_layout(rect=[0, 0.08, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {save_path}")
    plt.close()

    return metrics_text


def main():
    # Find the latest results file or accept a path argument
    if len(sys.argv) > 1:
        result_path = sys.argv[1]
    else:
        results_dir = Path("backtest_results")
        files = sorted(results_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            print("No backtest results found in backtest_results/")
            return
        result_path = str(files[0])

    print(f"Loading: {result_path}")
    results = load_results(result_path)
    df = build_dataframe(results)
    metrics = compute_metrics(df, results["initial_capital"])

    ticker = results["ticker"]
    save_path = f"backtest_results/{ticker}_{results['start_date']}_{results['end_date']}_chart.png"
    metrics_text = plot_results(df, metrics, ticker, save_path)

    print(metrics_text)


if __name__ == "__main__":
    main()
