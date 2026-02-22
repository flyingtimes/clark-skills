---
name: hot-twitter
description: AI 影响者热门内容抓取 - 从 AI 领域影响者列表中抓取最新推文
---

# Hot Twitter Skill

你是 AI 影响者热门内容抓取助手。从预定义的 AI 影响者列表中抓取每个用户最新的 N 条推文完整内容。

## 配置文件

影响者列表存储在：`skills/hot-twitter/scripts/ai_influencers_list.json`

## 工作流程

1. **读取影响者列表**
   ```bash
   python3 skills/hot-twitter/scripts/fetch_user_tweets.py --list
   ```

2. **对每个用户抓取最新推文**
   - 使用浏览器访问用户主页
   - 提取推文链接
   - 使用 x-fetch 获取完整内容

3. **使用 x-fetch 获取推文完整内容**
   ```bash
   python3 skills/x-fetch/scripts/fetch_x.py "<tweet_url>"
   ```


## 使用方式

### 抓取所有用户最新 5 条推文
```
/hot-twitter --all --count 5
```

### 抓取指定用户最新推文
```
/hot-twitter --user karpathy --count 10
```

### 抓取指定分类用户
```
/hot-twitter --category "AI大佬/专家" --count 5
```

## 输出格式

```json
{
  "username": "karpathy",
  "name": "Andrej Karpathy",
  "category": "AI大佬/专家",
  "tweets": [
    {
      "tweet_id": "1234567890",
      "url": "https://x.com/karpathy/status/1234567890",
      "created_at": "2026-02-22T10:00:00Z",
      "text": "推文内容...",
      "likes": 1234,
      "retweets": 56,
      "replies": 23,
      "views": 45678,
      "media": ["image_url"]
    }
  ]
}
```

## 依赖

- requests: HTTP 请求库
- json: JSON 处理

## 错误处理

- 用户不存在：跳过并记录
- API 限制：等待后重试
- 网络错误：记录并继续下一个用户
