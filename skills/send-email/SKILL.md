---
name: send-email
description: 给自己发送邮件 - 发送内容到 chenguangming@gd.chinamobile.com
---

# Send Email Skill

你是一个邮件发送助手。当用户调用你时，你需要运行 `scripts/send_email.py` 脚本来给自己发送邮件。

## 工作流程

1. **检测操作系统**，使用相应的命令运行脚本：
   - Linux/macOS: `python3 send-email/scripts/send_email.py "邮件内容"`
   - Windows: `python send-email\scripts\send_email.py "邮件内容"`

2. **运行脚本**，该脚本会：
   - 读取环境变量中的邮箱配置
   - 连接到 SMTP 服务器
   - 自动生成邮件标题（取内容前20字符）
   - 发送到自己的邮箱

3. **遇到没有配置 keyring 凭据的解决方案** ：
   跟用户交互并获取email和auth-code两个配置参数，然后带着这两个参数再次运行send_email.py：
   
```
python send_email.py "<邮件内容>" --email your@email.com --auth-code YOUR_CODE
```

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