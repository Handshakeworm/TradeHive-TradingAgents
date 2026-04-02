"""
社交媒体情绪分析模块（零额外 API 依赖）
策略：在现有 yfinance 新闻数据上叠加 VADER 情绪评分，无需新增任何 API Key。
- VADER（Valence Aware Dictionary and sEntiment Reasoner）：
  专为金融/社交媒体短文本优化的规则+词典情绪分析器，完全离线运行。
- 同时支持 Reddit（可选，需要 Reddit API Key）作为额外社交数据源。

依赖：pip install vaderSentiment praw（praw 为可选，仅需 Reddit 时安装）
分工说明：本模块只做数据采集与情绪评分，不做向量化（向量化归 #3）
"""

from typing import Annotated
from datetime import datetime, timedelta
import os
import json
import pandas as pd


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


# ─────────────────────────────────────────────────────────────────────────────
# 工具函数（供 interface.py 注册为 Agent 可调用工具）
# ─────────────────────────────────────────────────────────────────────────────

def get_news_sentiment(
    ticker: Annotated[str, "Stock or crypto ticker symbol, e.g. NVDA, BTC"],
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    lookback_days: Annotated[int, "Days of news lookback window"] = 7,
) -> str:
    """
    获取新闻情绪分析报告：从 yfinance 拉取新闻标题后用 VADER 进行情绪评分。
    兼容实时（当日）和历史回测（任意日期）两种场景。
    返回格式化字符串，供情绪分析 Agent 直接消费。
    """
    try:
        import yfinance as yf
    except ImportError:
        return "yfinance 未安装，请运行: pip install yfinance"

    try:
        sia = _get_vader()
    except ImportError as e:
        return str(e)

    try:
        ticker_obj = yf.Ticker(ticker.upper())
        news_items = ticker_obj.news or []
    except Exception as e:
        return f"Error fetching news for {ticker}: {e}"

    # ⚠️ yfinance news API limitation:
    # ticker.news returns only the ~8 most recent articles regardless of date range.
    # Time filtering below is applied strictly to exclude any article outside the window,
    # but for historical backtesting (date far in the past) results may be sparse or empty.
    # For richer historical sentiment, consider integrating a news archive API.

    if not news_items:
        return f"No news found for {ticker} around {date}."

    ref_dt = datetime.strptime(date, "%Y-%m-%d")
    cutoff_start = ref_dt - timedelta(days=lookback_days)

    scored = []
    for item in news_items:
        pub_ts = item.get("providerPublishTime") or item.get("pubDate")
        title = item.get("title", "")
        summary = item.get("summary", "") or item.get("description", "")
        link = item.get("link", "")

        # 解析发布时间
        if isinstance(pub_ts, int):
            pub_dt = datetime.utcfromtimestamp(pub_ts)
        elif isinstance(pub_ts, str):
            try:
                pub_dt = datetime.fromisoformat(pub_ts.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pub_dt = ref_dt
        else:
            pub_dt = ref_dt

        # 过滤时间窗口
        if not (cutoff_start <= pub_dt <= ref_dt + timedelta(days=1)):
            continue

        # VADER 评分：标题 + 摘要拼接
        full_text = f"{title}. {summary}".strip()
        scores = sia.polarity_scores(full_text)
        compound = round(scores["compound"], 4)
        label = _label_sentiment(compound)

        scored.append({
            "date": pub_dt.strftime("%Y-%m-%d"),
            "title": title[:100],
            "sentiment": label,
            "compound": compound,
            "positive": round(scores["pos"], 4),
            "negative": round(scores["neg"], 4),
        })

    if not scored:
        return (
            f"No news found for {ticker} in the window "
            f"[{cutoff_start.strftime('%Y-%m-%d')} ~ {date}]."
        )

    df = pd.DataFrame(scored).sort_values("date", ascending=False)

    # 聚合统计
    avg_compound = df["compound"].mean()
    overall_label = _label_sentiment(avg_compound)
    pos_count = (df["sentiment"] == "POSITIVE").sum()
    neg_count = (df["sentiment"] == "NEGATIVE").sum()
    neu_count = (df["sentiment"] == "NEUTRAL").sum()

    lines = [
        f"# News Sentiment Report: {ticker.upper()}",
        f"# Reference date: {date} | Lookback: {lookback_days} days",
        f"# Source: yfinance news + VADER sentiment scoring\n",
        f"Overall Sentiment:   {overall_label} (avg compound score: {avg_compound:.4f})",
        f"Articles analyzed:   {len(df)}  "
        f"[POSITIVE: {pos_count}  NEUTRAL: {neu_count}  NEGATIVE: {neg_count}]\n",
        f"{'Date':<12} {'Sentiment':<10} {'Score':>7}  Title",
        "-" * 80,
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{row['date']:<12} {row['sentiment']:<10} {row['compound']:>7.4f}  {row['title']}"
        )

    # 写缓存（#3 向量库用）
    _save_sentiment_cache(df, ticker, date)

    return "\n".join(lines)


def get_reddit_sentiment(
    ticker: Annotated[str, "Stock or crypto ticker symbol"],
    date: Annotated[str, "Reference date in yyyy-mm-dd format"],
    subreddits: Annotated[str, "Comma-separated subreddits, e.g. 'wallstreetbets,stocks,investing'"] = "wallstreetbets,stocks,investing",
    limit: Annotated[int, "Max posts per subreddit"] = 25,
) -> str:
    """
    从 Reddit 抓取相关帖子并进行 VADER 情绪评分（可选功能）。
    需要在 .env 中配置：
      REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
    申请地址（免费）：https://www.reddit.com/prefs/apps
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "tradehive_sentiment/1.0")

    if not client_id or not client_secret:
        return (
            "Reddit credentials not configured.\n"
            "Please add to .env:\n"
            "  REDDIT_CLIENT_ID=your_id\n"
            "  REDDIT_CLIENT_SECRET=your_secret\n"
            "  REDDIT_USER_AGENT=tradehive_sentiment/1.0\n"
            "Apply at: https://www.reddit.com/prefs/apps (free)"
        )

    try:
        import praw
    except ImportError:
        return "praw 未安装，请运行: pip install praw"

    try:
        sia = _get_vader()
    except ImportError as e:
        return str(e)

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    scored = []
    ref_dt = datetime.strptime(date, "%Y-%m-%d")
    # 计算回溯天数窗口（默认抓近7天；time_filter 只是 Reddit 搜索参数，
    # 实际时间过滤在下方通过 post.created_utc 精确筛选）
    cutoff_start = ref_dt - timedelta(days=7)

    for sub_name in [s.strip() for s in subreddits.split(",")]:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.search(ticker, limit=limit, time_filter="month"):
                post_dt = datetime.utcfromtimestamp(post.created_utc)
                # 严格按时间窗口过滤：只保留 [cutoff_start, ref_dt] 范围内的帖子
                if not (cutoff_start <= post_dt <= ref_dt + timedelta(days=1)):
                    continue
                text = f"{post.title}. {post.selftext[:200]}".strip()
                scores = sia.polarity_scores(text)
                compound = round(scores["compound"], 4)
                scored.append({
                    "subreddit": sub_name,
                    "date": post_dt.strftime("%Y-%m-%d"),
                    "title": post.title[:90],
                    "score": post.score,
                    "sentiment": _label_sentiment(compound),
                    "compound": compound,
                })
        except Exception:
            continue

    if not scored:
        return f"No Reddit posts found for {ticker} across {subreddits}."

    df = pd.DataFrame(scored).sort_values("compound")
    avg_compound = df["compound"].mean()
    overall_label = _label_sentiment(avg_compound)

    lines = [
        f"# Reddit Sentiment Report: {ticker.upper()}",
        f"# Reference date: {date} | Subreddits: {subreddits}",
        f"# Source: Reddit API + VADER\n",
        f"Overall Sentiment:   {overall_label} (avg compound: {avg_compound:.4f})",
        f"Posts analyzed:      {len(df)}\n",
        f"{'Subreddit':<22} {'Date':<12} {'Sentiment':<10} {'Score':>7}  Title",
        "-" * 85,
    ]
    for _, row in df.iterrows():
        lines.append(
            f"{row['subreddit']:<22} {row['date']:<12} {row['sentiment']:<10} "
            f"{row['compound']:>7.4f}  {row['title']}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 内部工具：情绪数据缓存（供 #3 RAP 向量库读取）
# ─────────────────────────────────────────────────────────────────────────────

def _save_sentiment_cache(df: pd.DataFrame, ticker: str, date: str):
    """将情绪评分数据写入本地缓存，#3 可直接读取，无需重复采集。"""
    try:
        from .local_cache import save_dataframe
        save_dataframe(df, ticker, "sentiment", date, date)
    except Exception:
        pass
