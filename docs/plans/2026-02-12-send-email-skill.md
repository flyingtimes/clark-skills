# Send Email Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a send-email skill that sends emails to self using SMTP with auto-generated subject from content.

**Architecture:** Python-based skill using smtplib (stdlib) for SMTP, environment variables for credentials, SKILL.md for command routing with cross-platform detection.

**Tech Stack:** Python 3, smtplib, email/stdlib, argparse, python-dotenv

---

## Task 1: Create Skill Directory Structure

**Files:**
- Create: `skills/send-email/SKILL.md`
- Create: `skills/send-email/scripts/send_email.py`

**Step 1: Create SKILL.md**

Create `skills/send-email/SKILL.md`:

```markdown
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

3. **向用户反馈结果**：
   - 发送成功：显示确认信息
   - 发送失败：显示错误原因

## 使用示例

- `/send-email 记得下午3点开会`
- `/send-email 这是一个很长的邮件内容...`

## 错误处理

- **环境变量缺失**: 提示配置 .env 文件
- **认证失败**: 检查授权码是否正确
- **连接失败**: 检查网络和 SMTP 配置
```

**Step 2: Create scripts directory**

```bash
mkdir -p skills/send-email/scripts
```

**Step 3: Commit**

```bash
git add skills/send-email/
git commit -m "feat: add send-email skill structure with SKILL.md"
```

---

## Task 2: Implement SMTP Email Client

**Files:**
- Create: `skills/send-email/scripts/send_email.py`

**Step 1: Write the SMTP client implementation**

Create `skills/send-email/scripts/send_email.py`:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMTP邮件发送客户端 - 给自己发送邮件
使用授权码方式认证
"""

import smtplib
import sys
import os
from email.message import EmailMessage
import argparse

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class SmtpEmailClient:
    """SMTP邮件发送客户端"""

    # 常见邮箱服务器的SMTP配置
    SMTP_SERVERS = {
        'qq.com': ('smtp.qq.com', 465),
        '163.com': ('smtp.163.com', 465),
        '126.com': ('smtp.126.com', 465),
        'gmail.com': ('smtp.gmail.com', 465),
        'outlook.com': ('smtp.office365.com', 587),
        'chinamobile.com': ('smtp.chinamobile.com', 465),
        '139.com': ('smtp.139.com', 465),
    }

    def __init__(self, email_address: str, auth_code: str, server: str = None, port: int = None):
        """
        初始化SMTP客户端

        Args:
            email_address: 邮箱地址
            auth_code: 授权码（不是登录密码）
            server: SMTP服务器地址（可选，自动检测）
            port: SMTP端口（可选，默认465）
        """
        self.email_address = email_address
        self.auth_code = auth_code

        # 自动检测SMTP服务器
        if server is None:
            domain = email_address.split('@')[-1]
            if domain in self.SMTP_SERVERS:
                server, port = self.SMTP_SERVERS[domain]
            else:
                server = f'smtp.{domain}'
                port = 465

        self.server = server
        self.port = port

    def _generate_subject(self, content: str) -> str:
        """
        从邮件内容生成标题

        Args:
            content: 邮件正文

        Returns:
            生成的标题
        """
        if not content or not content.strip():
            return "来自 Claude 的邮件"

        preview = content.strip()[:20]
        if len(content.strip()) > 20:
            preview += "..."
        return preview

    def _create_message(self, subject: str, body: str, to_email: str = None) -> EmailMessage:
        """
        创建邮件消息

        Args:
            subject: 邮件标题
            body: 邮件正文
            to_email: 收件人邮箱（默认发送给自己）

        Returns:
            EmailMessage对象
        """
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = self.email_address
        msg['To'] = to_email or self.email_address
        msg.set_content(body)
        return msg

    def send_email(self, body: str, to_email: str = None) -> tuple[bool, str]:
        """
        发送邮件

        Args:
            body: 邮件正文
            to_email: 收件人邮箱（默认发送给自己）

        Returns:
            (是否成功, 消息)
        """
        try:
            # 生成标题
            subject = self._generate_subject(body)

            # 创建邮件
            msg = self._create_message(subject, body, to_email or self.email_address)

            # 连接并发送（使用SSL）
            if self.port == 465:
                with smtplib.SMTP_SSL(self.server, self.port) as smtp:
                    smtp.login(self.email_address, self.auth_code)
                    smtp.send_message(msg)
            else:
                # 对于587端口使用STARTTLS
                with smtplib.SMTP(self.server, self.port) as smtp:
                    smtp.starttls()
                    smtp.login(self.email_address, self.auth_code)
                    smtp.send_message(msg)

            return True, f"邮件已发送: {subject}"

        except smtplib.SMTPAuthenticationError:
            return False, "认证失败：请检查授权码是否正确"
        except smtplib.SMTPConnectError as e:
            return False, f"连接失败：无法连接到 {self.server}:{self.port} - {e}"
        except Exception as e:
            return False, f"发送失败: {e}"


def main():
    """主函数"""
    # 加载.env文件（如果可用）
    if DOTENV_AVAILABLE:
        load_dotenv()

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='给自己发送邮件')
    parser.add_argument('content', nargs='?', help='邮件内容')
    parser.add_argument('--message', help='邮件内容（替代参数）')
    args = parser.parse_args()

    # 获取邮件内容
    content = args.content or args.message or ""
    if not content:
        print("错误: 请提供邮件内容")
        print("用法: python send_email.py \"邮件内容\"")
        sys.exit(1)

    # 从环境变量读取配置
    email_address = os.getenv('EMAIL_ADDRESS')
    auth_code = os.getenv('AUTH_CODE')
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')

    if not email_address or not auth_code:
        print("错误: 请在 .env 文件中配置 EMAIL_ADDRESS 和 AUTH_CODE")
        sys.exit(1)

    # 解析端口
    port = int(smtp_port) if smtp_port else None

    # 创建客户端并发送
    client = SmtpEmailClient(email_address, auth_code, smtp_server, port)
    success, message = client.send_email(content)

    if success:
        print(f"[OK] {message}")
    else:
        print(f"[X] {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add skills/send-email/scripts/send_email.py
git commit -m "feat: implement SMTP email client with auto-generated subject"
```

---

## Task 3: Register Skill in Plugin Manifest

**Files:**
- Modify: `.claude-plugin/plugin.json`

**Step 1: Read current plugin.json**

```bash
cat .claude-plugin/plugin.json
```

**Step 2: Add send-email skill to the skills list**

Add the new skill entry to the `skills` array in plugin.json:

```json
{
  "name": "send-email",
  "path": "skills/send-email/SKILL.md"
}
```

**Step 3: Verify plugin.json is valid JSON**

```bash
python -m json.tool .claude-plugin/plugin.json
```

**Step 4: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: register send-email skill in plugin manifest"
```

---

## Task 4: Manual Testing

**Files:**
- Test: `skills/send-email/scripts/send_email.py`

**Step 1: Test with Python directly**

```bash
cd skills/send-email/scripts
python send_email.py "测试邮件内容"
```

Expected: `[OK] 邮件已发送: 测试邮件内容` OR error if credentials not set

**Step 2: Test long content**

```bash
python send_email.py "这是一个非常长的邮件内容用来测试自动生成的标题是否会正确截断并添加省略号"
```

Expected: Subject should be `这是一个非常长的邮件内容...`

**Step 3: Test empty content handling**

```bash
python send_email.py ""
```

Expected: Error message asking for content

**Step 4: Verify email received**

Check email inbox for the sent messages

---

## Task 5: Update Documentation

**Files:**
- Modify: `README.md` (if it exists and has skills section)

**Step 1: Check if README.md has skills section**

```bash
grep -n "skills\|技能" README.md || echo "No skills section found"
```

**Step 2: Add send-email to skills list (if applicable)**

If README has a skills section, add:

```markdown
- **send-email**: 给自己发送邮件
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add send-email skill to README"
```

---

## Verification Checklist

After implementation, verify:

- [ ] Skill directory exists at `skills/send-email/`
- [ ] SKILL.md has correct frontmatter (name, description)
- [ ] `send_email.py` is executable and has proper shebang
- [ ] Plugin manifest (`plugin.json`) includes the new skill
- [ ] Cross-platform commands are correctly specified in SKILL.md
- [ ] Title is auto-generated from first 20 chars of content
- [ ] Environment variables (EMAIL_ADDRESS, AUTH_CODE) are used
- [ ] Error handling covers missing credentials, auth failure, connection failure
- [ ] Manual test email was sent and received successfully
