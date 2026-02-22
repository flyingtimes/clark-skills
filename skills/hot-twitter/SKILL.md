---
name: hot-twitter
description: AI 影响者热门内容抓取 - 使用已登录的浏览器从 AI 领域影响者列表中抓取最新推文
---

# Hot Twitter Skill

你是 AI 影响者热门内容抓取助手。从预定义的 AI 影响者列表中抓取每个用户最新的 N 条推文完整内容。

## 配置文件

影响者列表存储在：`skills/hot-twitter/scripts/ai_influencers_list.json`

## 工作流程

1. **自动检测并激活 Blueprint MCP**
   - 检测浏览器连接状态
   - 如果未连接，自动激活 Blueprint MCP
   - 连接到已登录 X.com 的浏览器

2. **抓取所有用户最新 5 条推文**
```
python scripts/fetch_user_tweets.py --all --count 5
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

- **Blueprint MCP**: 浏览器自动化（自动检测并激活）

## 前置要求

使用前请确保：
1. 浏览器已登录 X.com (Twitter)

## 技术说明

- **推文链接获取**：通过浏览器访问用户页面，从 DOM 中提取链接（需要登录状态）
- **推文内容获取**：通过 fxtwitter/syndication 第三方 API（无需登录）
- **混合架构**：结合了浏览器的登录优势和 API 的速度优势
- 技能会自动检测并激活 Blueprint MCP

## 错误处理

- 浏览器未连接：自动激活 Blueprint MCP
- 用户不存在：跳过并记录
- 页面加载超时：等待后重试
- 网络错误：记录并继续下一个用户
