---
name: send-email
description: 给自己发送邮件 - 发送内容到 chenguangming@gd.chinamobile.com
---

# Send Email Skill

你是一个邮件发送助手。当用户调用你时，你需要运行 `scripts/send_email.py` 脚本来给自己发送邮件。

## 工作流程

1. **检测.env文件是否存在
   看看send_email.py 的相同目录下是否存在.env文件，如果不存在则通过与用户对话获取EMAIL_ADDRESS和AUTH_CODE，并在send_email.py 的相同目录下创建.env文件内容。

   标准的.env文件格式如下：
   ```
# Email configuration for send-email skill
EMAIL_ADDRESS=<完整的email地址>
AUTH_CODE=<授权码>

# Optional SMTP configuration (auto-detected from email domain)
# SMTP_SERVER=smtp.chinamobile.com
# SMTP_PORT=465
   ```

2. **检测操作系统**，使用相应的命令运行脚本：
   - Linux/macOS: `python3 send-email/scripts/send_email.py "邮件内容"`
   - Windows: `python send-email\scripts\send_email.py "邮件内容"`

3. **运行脚本**，该脚本会：
   - 读取环境变量中的邮箱配置
   - 连接到 SMTP 服务器
   - 自动生成邮件标题（取内容前20字符）
   - 发送到自己的邮箱

4. **向用户反馈结果**：
   - 发送成功：显示确认信息
   - 发送失败：显示错误原因

## 使用示例

- `/send-email 记得下午3点开会`
- `/send-email 这是一个很长的邮件内容...`

## 错误处理

- **环境变量缺失**: 提示配置 .env 文件
- **认证失败**: 检查授权码是否正确
- **连接失败**: 检查网络和 SMTP 配置