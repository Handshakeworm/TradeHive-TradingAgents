"""
情绪���析模块
- VADER（Valence Aware Dictionary and sEntiment Reasoner）：
  专为金融/社交媒体短文本优化的规则+词典情绪分析器，完全离线运行。
- Reddit（可选，需要 Reddit API Key）作为社交数据源。
- 新闻情绪已由 Alpha Vantage NEWS_SENTIMENT API 自带，不再需要本地 VADER 评分。

依赖：pip install vaderSentiment praw（praw 为可选，仅需 Reddit 时安装）
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Annotated


# ─────────────────────────────────────────────────────────────────────────────
# Alpha Vantage NEWS_SENTIMENT 聚合
# ─────────────────────────────────────────────────────────────────────────────

def get_sentiment_summary(ticker: str, start_date: str, end_date: str) -> str:
    """
    从 bulk cache 中读取新闻 JSON，按日聚合 ticker 的情绪评分，返回格式化表格。

    Args:
        ticker: 股票代码，如 "NVDA"
        start_date: 开始日期 yyyy-mm-dd
        end_date: 结束日期 yyyy-mm-dd

    Returns:
        按日汇总的情绪统计表格字符串
    """
    from tradingagents.dataflows.bulk_cache import bulk_has, bulk_load

    # 读取缓存新闻（新闻缓存扩展名为 .txt）
    if not bulk_has(ticker, "news", ext=".txt"):
        return f"No cached news data found for {ticker}."

    raw = bulk_load(ticker, "news", ext=".txt")
    if not raw:
        return f"Failed to load news cache for {ticker}."

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return f"Invalid news cache format for {ticker}."

    feed = data.get("feed", [])
    if not feed:
        return f"No news articles found for {ticker}."

    # 日期范围过滤
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    # 按日聚合
    daily: dict[str, list[float]] = defaultdict(list)

    for article in feed:
        tp = article.get("time_published", "")
        if len(tp) < 8:
            continue
        try:
            article_dt = datetime.strptime(tp[:15], "%Y%m%dT%H%M%S")
        except ValueError:
            try:
                article_dt = datetime.strptime(tp[:8], "%Y%m%d")
            except ValueError:
                continue

        if not (start_dt <= article_dt <= end_dt):
            continue

        date_key = article_dt.strftime("%Y-%m-%d")

        # 优先用 ticker_sentiment，降级到 overall_sentiment
        ticker_upper = ticker.upper()
        ticker_score = None
        for ts in article.get("ticker_sentiment", []):
            if ts.get("ticker", "").upper() == ticker_upper:
                try:
                    ticker_score = float(ts["ticker_sentiment_score"])
                except (KeyError, ValueError):
                    pass
                break

        if ticker_score is None:
            raw_score = article.get("overall_sentiment_score")
            if raw_score is None:
                continue
            try:
                ticker_score = float(raw_score)
            except (TypeError, ValueError):
                continue

        daily[date_key].append(ticker_score)

    if not daily:
        return f"No news articles found for {ticker} between {start_date} and {end_date}."

    # 构建输出表格
    lines = [
        f"# Sentiment Summary for {ticker.upper()} ({start_date} to {end_date})",
        "",
        "| Date | Avg Score | Label | Bullish | Neutral | Bearish | Articles |",
        "|------|-----------|-------|---------|---------|---------|----------|",
    ]

    for date in sorted(daily.keys()):
        scores = daily[date]
        avg = sum(scores) / len(scores)
        bullish = sum(1 for s in scores if s >= 0.15)
        bearish = sum(1 for s in scores if s <= -0.15)
        neutral = len(scores) - bullish - bearish
        total = len(scores)

        if avg >= 0.35:
            label = "Bullish"
        elif avg >= 0.15:
            label = "Somewhat-Bullish"
        elif avg <= -0.35:
            label = "Bearish"
        elif avg <= -0.15:
            label = "Somewhat-Bearish"
        else:
            label = "Neutral"

        lines.append(
            f"| {date} | {avg:+.3f} | {label} | {bullish} | {neutral} | {bearish} | {total} |"
        )

    # 整体汇总
    all_scores = [s for scores in daily.values() for s in scores]
    overall_avg = sum(all_scores) / len(all_scores)
    lines += [
        "",
        f"**Overall period avg: {overall_avg:+.3f} | Total articles: {len(all_scores)}**",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# VADER 情绪评分核心
# ─────────────────────────────────────────────────────────────────────────────

def _get_vader():
    """获取 VADER 情绪分析器实例（懒加载）。"""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        return SentimentIntensityAnalyzer()
    except ImportError:
        raise ImportError(
            "vaderSentiment 未安装，请运行: pip install vaderSentiment"
        )


def score_text_sentiment(text: str) -> dict:
    """
    对单条文本进行 VADER 情绪评分。
    返回: {"positive": float, "negative": float, "neutral": float, "compound": float}
    compound 分值: -1（极负面）到 +1（极正面），>0.05 为正面，<-0.05 为负面
    """
    sia = _get_vader()
    scores = sia.polarity_scores(text)
    return {
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "compound": round(scores["compound"], 4),
    }


def _label_sentiment(compound: float) -> str:
    """将 compound 分值转换为可读标签。"""
    if compound >= 0.05:
        return "POSITIVE"
    elif compound <= -0.05:
        return "NEGATIVE"
    return "NEUTRAL"


