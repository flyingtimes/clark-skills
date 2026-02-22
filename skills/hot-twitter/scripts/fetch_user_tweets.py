#!/usr/bin/env python3
"""
Hot Twitter - AI Influencer Tweet Fetcher
抓取 AI 影响者的最新推文内容
用法: python fetch_user_tweets.py <command> [options]
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
import re
import requests

# 配置路径 - 从脚本目录定位
SCRIPT_DIR = Path(__file__).parent  # hot-twitter/scripts/
INFLUENCERS_FILE = SCRIPT_DIR / "ai_influencers_list.json"
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # 回到项目根目录
OUTPUT_DIR = PROJECT_ROOT / "hot-twitter_data"


# ==================== X-Fetch 集成功能 ====================

def extract_tweet_id(url):
    """从 URL 提取 tweet ID"""
    patterns = [
        r'(?:x\.com|twitter\.com)/\w+/status/(\d+)',
        r'(?:x\.com|twitter\.com)/\w+/statuses/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_username(url):
    """从 URL 提取用户名"""
    match = re.search(r'(?:x\.com|twitter\.com)/(\w+)/status', url)
    return match.group(1) if match else None


def fetch_via_fxtwitter(url):
    """通过 fxtwitter API 获取内容"""
    api_url = re.sub(r'(x\.com|twitter\.com)', 'api.fxtwitter.com', url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        return None


def fetch_via_syndication(tweet_id):
    """通过 X 的 syndication API 获取内容"""
    url = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        return None


def extract_article_content(article):
    """从 X Article 中提取完整内容"""
    if not article:
        return None

    content_blocks = article.get("content", {}).get("blocks", [])

    # 拼接所有文本块
    paragraphs = []
    for block in content_blocks:
        text = block.get("text", "").strip()
        block_type = block.get("type", "unstyled")

        if text:
            # 根据类型添加格式
            if block_type == "header-one":
                paragraphs.append(f"# {text}")
            elif block_type == "header-two":
                paragraphs.append(f"## {text}")
            elif block_type == "header-three":
                paragraphs.append(f"### {text}")
            elif block_type == "blockquote":
                paragraphs.append(f"> {text}")
            elif block_type == "unordered-list-item":
                paragraphs.append(f"- {text}")
            elif block_type == "ordered-list-item":
                paragraphs.append(f"1. {text}")
            else:
                paragraphs.append(text)

    return "\n\n".join(paragraphs)


def format_tweet_output(data, source):
    """格式化推文输出"""
    result = {
        "source": source,
        "success": True,
        "type": "tweet",
        "content": {}
    }

    if source == "fxtwitter":
        tweet = data.get("tweet", {})
        article = tweet.get("article")

        if article:
            # X Article 长文章
            result["type"] = "article"
            result["content"] = {
                "title": article.get("title", ""),
                "preview": article.get("preview_text", ""),
                "full_text": extract_article_content(article),
                "cover_image": article.get("cover_media", {}).get("media_info", {}).get("original_img_url"),
                "author": tweet.get("author", {}).get("name", ""),
                "username": tweet.get("author", {}).get("screen_name", ""),
                "created_at": article.get("created_at", ""),
                "modified_at": article.get("modified_at", ""),
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "views": tweet.get("views", 0),
                "bookmarks": tweet.get("bookmarks", 0)
            }
        else:
            # 普通推文
            result["content"] = {
                "text": tweet.get("text", ""),
                "author": tweet.get("author", {}).get("name", ""),
                "username": tweet.get("author", {}).get("screen_name", ""),
                "created_at": tweet.get("created_at", ""),
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
                "views": tweet.get("views", 0),
                "media": [m.get("url") for m in tweet.get("media", {}).get("all", []) if m.get("url")],
                "replies": tweet.get("replies", 0)
            }

    elif source == "syndication":
        result["content"] = {
            "text": data.get("text", ""),
            "author": data.get("user", {}).get("name", ""),
            "username": data.get("user", {}).get("screen_name", ""),
            "created_at": data.get("created_at", ""),
            "likes": data.get("favorite_count", 0),
            "retweets": data.get("retweet_count", 0),
            "media": [m.get("media_url_https") for m in data.get("mediaDetails", []) if m.get("media_url_https")]
        }

    return result


def fetch_tweet(url):
    """抓取推文内容（集成 x-fetch 功能）"""
    tweet_id = extract_tweet_id(url)
    username = extract_username(url)

    if not tweet_id:
        return {"success": False, "error": "无法从 URL 提取 tweet ID"}

    # 方法1: fxtwitter API (支持 Article)
    data = fetch_via_fxtwitter(url)
    if data and data.get("tweet"):
        return format_tweet_output(data, "fxtwitter")

    # 方法2: syndication API
    data = fetch_via_syndication(tweet_id)
    if data and data.get("text"):
        return format_tweet_output(data, "syndication")

    return {"success": False, "error": "所有抓取方式均失败"}

# ==================== 主程序功能 ====================

def load_influencers():
    """加载影响者列表"""
    try:
        with open(INFLUENCERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        influencers = []
        for category in data.get('ai_influencers', []):
            for user in category.get('users', []):
                user_info = {
                    'username': user.get('username'),
                    'name': user.get('name', ''),
                    'bio': user.get('bio', ''),
                    'category': category.get('category', '未分类'),
                    'url': user.get('url', '')
                }
                influencers.append(user_info)
        return influencers
    except Exception as e:
        print(f"Error loading influencers: {e}", file=sys.stderr)
        return []


def fetch_user_tweets(username, count=5):
    """
    抓取指定用户的推文
    用户手动输入推文 URL
    """
    print(f"\n{'='*60}")
    print(f"抓取用户: @{username}")
    print(f"需要最新 {count} 条推文")
    print(f"{'='*60}")
    print("\n请手动访问以下页面并复制推文链接:")
    print(f"  https://x.com/{username}")
    print(f"  https://x.com/{username}/with_replies")
    print("\n然后将推文 URL 粘贴到这里 (每行一个，输入空行结束):\n")

    tweet_urls = []
    while len(tweet_urls) < count:
        try:
            url = input(f"推文 #{len(tweet_urls) + 1} URL: ").strip()
            if not url:
                break
            if extract_tweet_id(url):
                tweet_urls.append(url)
            else:
                print("  无效的推文 URL，请重新输入")
        except (EOFError, KeyboardInterrupt):
            break

    results = []
    for i, url in enumerate(tweet_urls, 1):
        print(f"\n[{i}/{len(tweet_urls)}] 抓取: {url}")
        content = fetch_tweet(url)
        if content and content.get('success'):
            tweet_data = content.get('content', {})
            tweet_data['url'] = url
            tweet_data['tweet_id'] = extract_tweet_id(url)
            tweet_data['source'] = content.get('source', 'unknown')
            results.append(tweet_data)
            print(f"  ✓ 成功: {tweet_data.get('text', '')[:50]}...")
        else:
            print(f"  ✗ 失败: {content.get('error', '未知错误')}")
        time.sleep(1)  # 避免请求过快

    return {
        "username": username,
        "fetched_at": datetime.now().isoformat(),
        "tweet_count": len(results),
        "tweets": results
    }


def fetch_all_influencers(count=5, category_filter=None):
    """抓取所有影响者的推文"""
    influencers = load_influencers()

    if category_filter:
        influencers = [u for u in influencers if u.get('category') == category_filter]

    print(f"找到 {len(influencers)} 个影响者")
    print(f"每个用户抓取最新 {count} 条推文")

    results = []

    for i, influencer in enumerate(influencers, 1):
        username = influencer.get('username')
        name = influencer.get('name', username)
        category = influencer.get('category', '未分类')
        bio = influencer.get('bio', '')

        print(f"\n{'='*70}")
        print(f"[{i}/{len(influencers)}] 处理: {name} (@{username}) - {category}")
        print(f"{'='*70}")
        print(f"简介: {bio[:100]}...")

        # 抓取推文
        user_data = fetch_user_tweets(username, count)
        user_data['name'] = name
        user_data['category'] = category
        user_data['bio'] = bio
        user_data['url'] = influencer.get('url', '')

        results.append(user_data)

    return results


def save_results(results, filename=None):
    """保存结果到文件"""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tweets_{timestamp}.json"

    output_file = OUTPUT_DIR / filename

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 结果已保存到: {output_file}")
    return output_file


def print_summary(results):
    """打印结果摘要"""
    print("\n" + "="*70)
    print("抓取结果摘要")
    print("="*70)

    total_tweets = 0
    for user_data in results:
        username = user_data.get('username')
        count = user_data.get('tweet_count', 0)
        total_tweets += count
        name = user_data.get('name', username)
        print(f"  @{username} ({name}): {count} 条推文")

    print("-"*70)
    print(f"总计: {len(results)} 个用户, {total_tweets} 条推文")
    print("="*70)


def main():
    if len(sys.argv) < 2:
        print("Hot Twitter - AI 影响者推文抓取工具")
        print("\n用法: python fetch_user_tweets.py <command> [options]")
        print("\n命令:")
        print("  --all              抓取所有影响者")
        print("  --user <username>  抓取指定用户")
        print("  --list             列出所有影响者")
        print("\n选项:")
        print("  --count <n>        每个用户抓取的推文数 (默认: 5)")
        print("  --category <name>  只抓取指定分类")
        print("\n示例:")
        print("  python fetch_user_tweets.py --list")
        print("  python fetch_user_tweets.py --user karpathy --count 3")
        print("  python fetch_user_tweets.py --all --count 5")
        return

    command = sys.argv[1]
    count = 5
    category = None

    # 解析选项
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--count' and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--category' and i + 1 < len(sys.argv):
            category = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if command == '--list':
        influencers = load_influencers()
        print("\n=== AI 影响者列表 ===\n")
        current_cat = None
        for inf in influencers:
            cat = inf.get('category', '未分类')
            if cat != current_cat:
                current_cat = cat
                print(f"\n【{current_cat}】")
            print(f"  @{inf['username']} - {inf.get('name', '')}")
        print(f"\n总计: {len(influencers)} 位影响者")

    elif command == '--all':
        results = fetch_all_influencers(count, category)
        save_results(results)
        print_summary(results)

    elif command == '--user':
        if len(sys.argv) < 3 or sys.argv[2].startswith('--'):
            print("Error: --user requires a username")
            return
        username = sys.argv[2]
        result = fetch_user_tweets(username, count)
        save_results([result], f"{username}_tweets.json")
        print_summary([result])

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
