---
name: email
description: 通过 fetch_and_save.py 获取最新邮件 - 读取发件人、标题、正文、附件等信息
---

# Email Skill

你是一个邮件获取助手。当用户调用你时，你需要运行 `scripts/fetch_and_save.py` 脚本来获取最新的5封邮件。

## 工作流程

1. **检测操作系统**，使用相应的命令运行脚本：
   - Linux/macOS: `python3 email/scripts/fetch_and_save.py`
   - Windows: `python email\scripts\fetch_and_save.py`

2. **运行脚本**，该脚本会：
   - 连接到 IMAP 邮箱服务器
   - 获取最新的 5 封邮件
   - 将结果保存到 `email/scripts/emails_result.txt`

3. **读取并解析结果文件** `email/scripts/emails_result.txt`

4. **向用户展示邮件摘要**，包括：
   - 邮件数量
   - 每封邮件的发件人、标题、日期
   - 正文内容摘要
   - 附件信息（如有）

## 错误处理

如果遇到以下错误，请提示用户：

- **连接失败**: 检查网络连接和邮箱配置
- **认证失败**: 检查 `.env` 文件中的 `EMAIL_ADDRESS` 和 `AUTH_CODE` 是否正确
- **文件不存在**: 确保脚本路径正确

## 用户参数说明

用户可以通过参数指定：
- `limit`: 获取邮件数量（默认5封）
- `folder`: 邮箱文件夹（默认 INBOX）

示例调用：
- `/email` - 获取最新5封邮件
- `/email --limit 10` - 获取最新10封邮件
- `/email --folder Sent` - 获取已发送文件夹的邮件
