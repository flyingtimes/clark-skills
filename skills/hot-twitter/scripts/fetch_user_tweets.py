#!/usr/bin/env python3
"""
Hot Twitter - AI Influencer Tweet Fetcher
使用浏览器自动化抓取 AI 影响者的最新推文内容
用法: python fetch_user_tweets.py <command> [options]

此脚本使用 x-fetch 获取推文内容，浏览器用于获取推文链接
"""

import json
import sys
import time
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import re
import requests

# 配置路径 - 从脚本目录定位
SCRIPT_DIR = Path(__file__).parent  # hot-twitter/scripts/
INFLUENCERS_FILE = SCRIPT_DIR / "ai_influencers_list.json"
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # 回到项目根目录
OUTPUT_DIR = PROJECT_ROOT / "hot-twitter_data"
XFETCH_SCRIPT = PROJECT_ROOT / "skills" / "x-fetch" / "scripts" / "fetch_x.py"


# ==================== 日期筛选功能 ====================

def parse_twitter_date(date_str):
    """
    解析 Twitter 日期字符串

    支持格式：
    - "Mon Feb 19 16:08:33 +0000 2026"
    - 其他 Twitter API 返回的格式
    """
    if not date_str:
        return None

    # 尝试解析标准 Twitter 格式
    try:
        # Twitter 格式: "Mon Feb 19 16:08:33 +0000 2026"
        dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt
    except ValueError:
        pass

    # 尝试 ISO 格式
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        pass

    return None


def is_within_hours(date_str, hours=48):
    """
    检查推文是否在指定小时数内

    Args:
        date_str: Twitter 日期字符串
        hours: 小时数（默认48）

    Returns:
        bool: 是否在指定时间内
    """
    tweet_time = parse_twitter_date(date_str)
    if not tweet_time:
        return True  # 无法解析日期时默认保留

    cutoff_time = datetime.now(tweet_time.tzinfo) - timedelta(hours=hours)
    return tweet_time >= cutoff_time


def format_tweet_age(date_str):
    """格式化推文年龄为易读格式"""
    tweet_time = parse_twitter_date(date_str)
    if not tweet_time:
        return "未知时间"

    now = datetime.now(tweet_time.tzinfo)
    delta = now - tweet_time

    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f"{int(delta.total_seconds() / 60)}分钟前"
    elif hours < 24:
        return f"{int(hours)}小时前"
    else:
        return f"{int(hours / 24)}天前"


# ==================== 推文链接提取（需要浏览器执行）====================

def extract_tweet_links_javascript(count=3):
    """返回提取推文链接的 JavaScript 代码"""
    return f'''(function() {{
    const tweetUrls = [];
    const seen = new Set();

    // 滚动加载更多推文
    async function scrollAndCollect() {{
        for (let i = 0; i < 3; i++) {{
            window.scrollBy(0, 1000);
            await new Promise(r => setTimeout(r, 1000));
        }}
    }}

    function extractLinks() {{
        const links = document.querySelectorAll('a[href*="/status/"]');
        for (const link of links) {{
            const href = link.getAttribute('href');
            const match = href.match(/\\/status\\/(\\d+)/);
            if (match && !seen.has(match[1])) {{
                seen.add(match[1]);
                let fullUrl = href.startsWith('http') ? href : 'https://x.com' + href;
                tweetUrls.push(fullUrl);
            }}
        }}
    }}

    await scrollAndCollect();
    extractLinks();

    return JSON.stringify(tweetUrls.slice(0, {count}));
}})()'''


# ==================== 第三方 API 获取推文内容 ====================

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
    paragraphs = []
    for block in content_blocks:
        text = block.get("text", "").strip()
        block_type = block.get("type", "unstyled")

        if text:
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


def fetch_tweet_content_via_script(url):
    """通过 x-fetch 脚本获取推文详细内容"""
    try:
        result = subprocess.run(
            ['python3', str(XFETCH_SCRIPT), url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # 解析 JSON 输出
            output = result.stdout.strip()
            # 查找 JSON 对象
            match = re.search(r'\\{.*\\}', output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception as e:
        pass

    # 备用：直接调用 API
    return fetch_tweet_content_api(url)


def fetch_tweet_content_api(url):
    """直接通过 API 获取推文详细内容"""
    tweet_id = extract_tweet_id(url)

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

    return {"success": False, "error": "所有 API 方式均失败"}


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


def fetch_user_tweets_auto(username, count=10, browser_getter=None, hours_filter=48):
    """
    自动化抓取单个用户的推文

    Args:
        username: Twitter 用户名
        count: 获取推文数量（默认10，以便筛选后仍有足够内容）
        browser_getter: 可选的浏览器获取函数，接收 js_code 返回 urls 列表
        hours_filter: 时间筛选范围（小时数，默认48）
    """
    print(f"\n{'='*60}")
    print(f"抓取用户: @{username}")
    print(f"时间筛选: 最近 {hours_filter} 小时内")
    print(f"{'='*60}")

    # 获取推文链接
    if browser_getter:
        js_code = extract_tweet_links_javascript(count)
        tweet_urls = browser_getter(username, js_code)
    else:
        tweet_urls = get_tweets_via_file_exchange(username, count)

    if not tweet_urls:
        print(f"未获取到推文链接", file=sys.stderr)
        return {
            "username": username,
            "fetched_at": datetime.now().isoformat(),
            "tweet_count": 0,
            "tweets": [],
            "hours_filter": hours_filter
        }

    print(f"获取到 {len(tweet_urls)} 条推文链接")

    # 使用第三方 API 获取推文详细内容
    results = []
    filtered_count = 0

    for i, url in enumerate(tweet_urls, 1):
        print(f"\n[{i}/{len(tweet_urls)}] 抓取: {url}")
        content = fetch_tweet_content_api(url)

        if content and content.get('success'):
            tweet_data = content.get('content', {})
            tweet_data['url'] = url
            tweet_data['tweet_id'] = extract_tweet_id(url)
            tweet_data['source'] = content.get('source', 'unknown')

            # 检查日期筛选
            created_at = tweet_data.get('created_at', '')
            if is_within_hours(created_at, hours_filter):
                tweet_data['age'] = format_tweet_age(created_at)
                results.append(tweet_data)
                text_preview = tweet_data.get('text', '')[:50]
                age_info = tweet_data.get('age', '未知时间')
                print(f"  ✓ 成功 ({content.get('source')}) - {age_info}: {text_preview}...")
            else:
                filtered_count += 1
                age_info = format_tweet_age(created_at)
                print(f"  ⊗ 过滤 ({age_info})")
        else:
            print(f"  ✗ 失败: {content.get('error', '未知错误')}")

        time.sleep(1)

    print(f"\n结果: 保留 {len(results)} 条, 过滤 {filtered_count} 条")

    return {
        "username": username,
        "fetched_at": datetime.now().isoformat(),
        "tweet_count": len(results),
        "tweets": results,
        "hours_filter": hours_filter,
        "filtered_count": filtered_count
    }


def get_tweets_via_file_exchange(username, count=3):
    """通过文件交换获取推文链接"""
    # 创建临时文件用于交换数据
    temp_file = OUTPUT_DIR / f"temp_{username}_urls.json"
    temp_file.parent.mkdir(exist_ok=True)

    # 写入 JavaScript 代码到文件
    js_code = extract_tweet_links_javascript(count)
    js_file = OUTPUT_DIR / f"temp_{username}_js.js"
    with open(js_file, 'w') as f:
        f.write(js_code)

    print(f"\n>>> 浏览器操作步骤:")
    print(f"1. 导航到: https://x.com/{username}")
    print(f"2. 执行 JavaScript: {js_file}")
    print(f"3. 将结果保存到: {temp_file}")
    print(f"\n按 Enter 完成后继续...", file=sys.stderr)
    input()

    # 读取结果
    if temp_file.exists():
        with open(temp_file, 'r') as f:
            tweet_urls = json.load(f)
        # 清理临时文件
        temp_file.unlink()
        js_file.unlink()
        return tweet_urls

    return []


def fetch_all_influencers_auto(count=10, category_filter=None, browser_getter=None, hours_filter=48):
    """自动化抓取所有影响者的推文"""
    influencers = load_influencers()

    if category_filter:
        influencers = [u for u in influencers if u.get('category') == category_filter]

    print(f"找到 {len(influencers)} 个影响者")
    print(f"每个用户抓取最新 {count} 条推文")
    print(f"时间筛选: 最近 {hours_filter} 小时内")

    results = []

    for i, influencer in enumerate(influencers, 1):
        username = influencer.get('username')
        name = influencer.get('name', username)
        category = influencer.get('category', '未分类')

        print(f"\n{'='*70}")
        print(f"[{i}/{len(influencers)}] 处理: {name} (@{username}) - {category}")
        print(f"{'='*70}")

        # 抓取推文
        user_data = fetch_user_tweets_auto(username, count, browser_getter, hours_filter)
        user_data['name'] = name
        user_data['category'] = category
        user_data['bio'] = influencer.get('bio', '')
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
        print("  --count <n>        每个用户抓取的推文数 (默认: 10)")
        print("  --hours <n>        时间筛选范围，单位小时 (默认: 48)")
        print("  --category <name>  只抓取指定分类")
        print("\n示例:")
        print("  python fetch_user_tweets.py --list")
        print("  python fetch_user_tweets.py --user karpathy --count 5")
        print("  python fetch_user_tweets.py --all --hours 24")
        print("\n说明:")
        print("  - 默认筛选最近48小时内的推文")
        print("  - 使用 --hours 0 可不过滤任何推文")
        return

    command = sys.argv[1]
    count = 10
    hours_filter = 48
    category = None

    # 解析选项
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--count' and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--hours' and i + 1 < len(sys.argv):
            hours_filter = int(sys.argv[i + 1])
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
        results = fetch_all_influencers_auto(count, category, None, hours_filter)
        if results:
            save_results(results)
            print_summary(results)

    elif command == '--user':
        if len(sys.argv) < 3 or sys.argv[2].startswith('--'):
            print("Error: --user requires a username")
            return
        username = sys.argv[2]
        result = fetch_user_tweets_auto(username, count, None, hours_filter)
        save_results([result], f"{username}_tweets.json")
        print_summary([result])

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
