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