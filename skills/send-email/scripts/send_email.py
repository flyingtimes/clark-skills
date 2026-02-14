#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMTP邮件发送客户端 - 给自己发送邮件
使用授权码方式认证
优先使用 keyring 存储凭据，降级到环境变量
"""

import smtplib
import sys
import os
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import argparse
import mimetypes

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

KEYRING_SERVICE = "my-claude-skills"


class SmtpEmailClient:
    """SMTP邮件发送客户端"""

    # 常见邮箱服务器的SMTP配置
    SMTP_SERVERS = {
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

        # 移除换行符，避免邮件头错误
        clean_content = content.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        preview = clean_content.strip()[:20]
        if len(clean_content.strip()) > 20:
            preview += "..."
        return preview

    def _create_message(self, subject: str, body: str, to_email: str = None,
                        images: list = None, attachments: list = None):
        """
        创建邮件消息

        Args:
            subject: 邮件标题
            body: 邮件正文（支持HTML）
            to_email: 收件人邮箱（默认发送给自己）
            images: 图片路径列表，会嵌入到邮件正文中
            attachments: 附件路径列表

        Returns:
            EmailMessage或MIMEMultipart对象
        """
        # 如果有图片或附件，使用MIMEMultipart
        if images or attachments:
            msg = MIMEMultipart('related')
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = to_email or self.email_address

            # 处理图片嵌入
            if images:
                # 检查body是否包含HTML，如果不是则转换
                body_html = body if '<' in body and '>' in body else f"<p>{body.replace(chr(10), '<br>')}</p>"

                for idx, img_path in enumerate(images):
                    if not os.path.exists(img_path):
                        print(f"警告: 图片不存在 {img_path}")
                        continue

                    # 读取图片
                    with open(img_path, 'rb') as f:
                        img_data = f.read()

                    # 检测图片类型
                    img_type, _ = mimetypes.guess_type(img_path)
                    if not img_type or not img_type.startswith('image/'):
                        img_type = 'image/jpeg'

                    subtype = img_type.split('/')[1]

                    # 添加图片作为内嵌附件
                    img_cid = f"img{idx}"
                    msg_attachment = MIMEImage(img_data, _subtype=subtype)
                    msg_attachment.add_header('Content-ID', f'<{img_cid}>')
                    msg_attachment.add_header('Content-Disposition', 'inline', filename=os.path.basename(img_path))
                    msg.attach(msg_attachment)

                    # 在body中插入图片引用
                    img_tag = f'<br><img src="cid:{img_cid}" alt="image">'
                    body_html += img_tag

                # 设置HTML正文
                msg_alternative = MIMEMultipart('alternative')
                msg_text = MIMEText(body, 'plain', 'utf-8')
                msg_html = MIMEText(body_html, 'html', 'utf-8')
                msg_alternative.attach(msg_text)
                msg_alternative.attach(msg_html)
                msg.attach(msg_alternative)

            # 处理普通附件
            if attachments:
                for attach_path in attachments:
                    if not os.path.exists(attach_path):
                        print(f"警告: 附件不存在 {attach_path}")
                        continue

                    with open(attach_path, 'rb') as f:
                        attach_data = f.read()

                    attach_type, _ = mimetypes.guess_type(attach_path)
                    if not attach_type:
                        attach_type = 'application/octet-stream'

                    main_type, subtype = attach_type.split('/', 1) if '/' in attach_type else ('application', 'octet-stream')

                    from email.mime.base import MIMEBase
                    import email.encoders

                    part = MIMEBase(main_type, subtype)
                    part.set_payload(attach_data)
                    email.encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment',
                                    filename=os.path.basename(attach_path))
                    msg.attach(part)
        else:
            # 简单文本邮件
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = self.email_address
            msg['To'] = to_email or self.email_address

            # 检测是否为HTML内容
            if '<html>' in body.lower() or '<body>' in body.lower() or '<table>' in body.lower():
                msg.set_content(body, subtype='html')
            else:
                msg.set_content(body)

        return msg

    def send_email(self, body: str, to_email: str = None,
                   images: list = None, attachments: list = None) -> tuple[bool, str]:
        """
        发送邮件

        Args:
            body: 邮件正文
            to_email: 收件人邮箱（默认发送给自己）
            images: 图片路径列表，会嵌入到邮件正文中
            attachments: 附件路径列表

        Returns:
            (是否成功, 消息)
        """
        try:
            # 生成标题
            subject = self._generate_subject(body)

            # 创建邮件
            msg = self._create_message(subject, body, to_email or self.email_address,
                                       images=images, attachments=attachments)

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

            extra_info = ""
            if images:
                extra_info = f" (包含{len(images)}张图片)"
            elif attachments:
                extra_info = f" (包含{len(attachments)}个附件)"

            return True, f"邮件已发送: {subject}{extra_info}"

        except smtplib.SMTPAuthenticationError:
            return False, "认证失败：请检查授权码是否正确"
        except smtplib.SMTPConnectError as e:
            return False, f"连接失败：无法连接到 {self.server}:{self.port} - {e}"
        except Exception as e:
            return False, f"发送失败: {e}"


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='给自己发送邮件')
    parser.add_argument('content', nargs='?', help='邮件内容')
    parser.add_argument('--message', help='邮件内容（替代参数）')
    parser.add_argument('--to', help='收件人邮箱（默认发送给自己）')
    parser.add_argument('--email', help='发件人邮箱地址')
    parser.add_argument('--auth-code', help='SMTP授权码')
    parser.add_argument('--image', '-i', action='append', dest='images',
                        help='添加图片到邮件正文（可多次使用）')
    parser.add_argument('--attach', '-a', action='append', dest='attachments',
                        help='添加附件（可多次使用）')
    args = parser.parse_args()

    # 获取邮件内容
    content = args.content or args.message or ""
    if not content:
        print("错误: 请提供邮件内容")
        print("用法: python send_email.py \"邮件内容\"")
        sys.exit(1)

    # 从 keyring 或环境变量读取配置（命令行参数优先）
    email_address = args.email
    auth_code = args.auth_code

    # 如果通过命令行提供了凭据，保存到 keyring
    if email_address and KEYRING_AVAILABLE:
        keyring.set_password(KEYRING_SERVICE, 'email_address', email_address)
    if not email_address and KEYRING_AVAILABLE:
        email_address = keyring.get_password(KEYRING_SERVICE, 'email_address')

    if auth_code and KEYRING_AVAILABLE:
        keyring.set_password(KEYRING_SERVICE, 'auth_code', auth_code)
    if not auth_code and KEYRING_AVAILABLE:
        auth_code = keyring.get_password(KEYRING_SERVICE, 'auth_code')

    smtp_server = None
    smtp_port = None

    if KEYRING_AVAILABLE:
        smtp_server = keyring.get_password(KEYRING_SERVICE, 'smtp_server')
        smtp_port_str = keyring.get_password(KEYRING_SERVICE, 'smtp_port')
        smtp_port = int(smtp_port) if smtp_port_str else None

    if not email_address or not auth_code:
        if KEYRING_AVAILABLE:
            print("错误: 请先配置 keyring 凭据或使用命令行参数")
            print(f"  命令行: python send_email.py \"内容\" --email your@email.com --auth-code YOUR_CODE")
            print(f"  设置命令: python -c \"import keyring; keyring.set_password('{KEYRING_SERVICE}', 'email_address', 'your@email.com')\"")
            print(f"              python -c \"import keyring; keyring.set_password('{KEYRING_SERVICE}', 'auth_code', 'your_auth_code')\"")
        else:
            print("错误: 请使用命令行参数或配置环境变量")
            print(f"  命令行: python send_email.py \"内容\" --email your@email.com --auth-code YOUR_CODE")
            print(f"  环境变量: EMAIL_ADDRESS 和 AUTH_CODE")
        sys.exit(1)

    # 创建客户端并发送
    client = SmtpEmailClient(email_address, auth_code, smtp_server, smtp_port)
    to_email = args.to if args.to else None
    success, message = client.send_email(content, to_email,
                                        images=args.images,
                                        attachments=args.attachments)

    if success:
        print(f"[OK] {message}")
    else:
        print(f"[X] {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()