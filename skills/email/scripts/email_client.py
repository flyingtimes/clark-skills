#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMAP邮箱客户端 - 读取发件人、标题、正文、附件等信息
使用授权码方式认证
"""

import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email import message as email_message
import os
from typing import List, Dict, Optional

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


class ImapEmailClient:
    """IMAP邮件客户端"""

    # 常见邮箱服务器的IMAP配置
    IMAP_SERVERS = {
        'qq.com': ('imap.qq.com', 993),
        '163.com': ('imap.163.com', 993),
        '126.com': ('imap.126.com', 993),
        'gmail.com': ('imap.gmail.com', 993),
        'outlook.com': ('outlook.office365.com', 993),
        'chinamobile.com': ('imap.chinamobile.com', 993),
        '139.com': ('imap.139.com', 993),
    }

    def __init__(self, email_address: str, auth_code: str, server: str = None, port: int = None):
        """
        初始化IMAP客户端

        Args:
            email_address: 邮箱地址
            auth_code: 授权码（不是登录密码）
            server: IMAP服务器地址（可选，自动检测）
            port: IMAP端口（可选，默认993）
        """
        self.email_address = email_address
        self.auth_code = auth_code

        # 自动检测IMAP服务器
        if server is None:
            domain = email_address.split('@')[-1]
            if domain in self.IMAP_SERVERS:
                server, port = self.IMAP_SERVERS[domain]
            else:
                server = f'imap.{domain}'
                port = 993

        self.server = server
        self.port = port
        self.client: Optional[imaplib.IMAP4_SSL] = None
        self.connected = False

    def connect(self) -> bool:
        """
        连接到IMAP服务器

        Returns:
            连接是否成功
        """
        try:
            # 使用SSL连接
            self.client = imaplib.IMAP4_SSL(self.server, self.port)
            # 登录（使用授权码）
            self.client.login(self.email_address, self.auth_code)
            self.connected = True
            print(f"[OK] 已连接到 {self.server}:{self.port}")
            return True
        except Exception as e:
            print(f"[X] 连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.client and self.connected:
            try:
                self.client.close()
                self.client.logout()
            except:
                pass
            finally:
                self.connected = False
                print("[OK] 已断开连接")

    @classmethod
    def get_credentials(cls, email_address: str = None, auth_code: str = None) -> tuple:
        """
        从 keyring 或环境变量获取凭据

        Args:
            email_address: 邮箱地址（命令行参数）
            auth_code: 授权码（命令行参数）

        Returns:
            (email_address, auth_code, imap_server, imap_port)
        """
        # 如果通过命令行提供了凭据，保存到 keyring
        if email_address and KEYRING_AVAILABLE:
            keyring.set_password(KEYRING_SERVICE, 'email_address', email_address)
        if not email_address and KEYRING_AVAILABLE:
            email_address = keyring.get_password(KEYRING_SERVICE, 'email_address')

        if auth_code and KEYRING_AVAILABLE:
            keyring.set_password(KEYRING_SERVICE, 'auth_code', auth_code)
        if not auth_code and KEYRING_AVAILABLE:
            auth_code = keyring.get_password(KEYRING_SERVICE, 'auth_code')

        # 降级到环境变量
        if not email_address:
            email_address = os.getenv('EMAIL_ADDRESS')
        if not auth_code:
            auth_code = os.getenv('AUTH_CODE')

        # 获取 IMAP 服务器配置
        imap_server = None
        imap_port = None
        if KEYRING_AVAILABLE:
            imap_server = keyring.get_password(KEYRING_SERVICE, 'imap_server')
            imap_port_str = keyring.get_password(KEYRING_SERVICE, 'imap_port')
            imap_port = int(imap_port_str) if imap_port_str else None

        return email_address, auth_code, imap_server, imap_port

    def _decode_header_value(self, header_value: str) -> str:
        """
        解码邮件头部字段

        Args:
            header_value: 头部字段原始值

        Returns:
            解码后的字符串
        """
        if header_value is None:
            return ""

        decoded_parts = []
        for content, encoding in decode_header(header_value):
            if isinstance(content, bytes):
                if encoding:
                    try:
                        decoded_parts.append(content.decode(encoding))
                    except (UnicodeDecodeError, LookupError):
                        decoded_parts.append(content.decode('utf-8', errors='ignore'))
                else:
                    decoded_parts.append(content.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(content))
        return ''.join(decoded_parts)

    def _get_email_body(self, msg: email_message.Message) -> Dict[str, Optional[str]]:
        """
        提取邮件正文

        Args:
            msg: 邮件消息对象

        Returns:
            包含plain和html正文的字典
        """
        body = {'plain': None, 'html': None}

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                # 跳过附件
                if 'attachment' in content_disposition:
                    continue

                # 获取文本正文
                if content_type == 'text/plain' and body['plain'] is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body['plain'] = payload.decode(charset)
                        except:
                            body['plain'] = payload.decode('utf-8', errors='ignore')

                # 获取HTML正文
                elif content_type == 'text/html' and body['html'] is None:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        try:
                            body['html'] = payload.decode(charset)
                        except:
                            body['html'] = payload.decode('utf-8', errors='ignore')
        else:
            # 非多部分邮件
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    body_content = payload.decode(charset)
                except:
                    body_content = payload.decode('utf-8', errors='ignore')

                content_type = msg.get_content_type()
                if content_type == 'text/html':
                    body['html'] = body_content
                else:
                    body['plain'] = body_content

        return body

    def _get_attachments(self, msg: email.message.Message) -> List[Dict[str, any]]:
        """
        提取附件信息

        Args:
            msg: 邮件消息对象

        Returns:
            附件信息列表
        """
        attachments = []

        for part in msg.walk():
            content_disposition = str(part.get('Content-Disposition', ''))

            if 'attachment' in content_disposition:
                filename = part.get_filename()
                if filename:
                    filename = self._decode_header_value(filename)
                    attachment_info = {
                        'filename': filename,
                        'size': len(part.get_payload(decode=True)) if part.get_payload() else 0,
                        'content_type': part.get_content_type(),
                    }
                    attachments.append(attachment_info)

        return attachments

    def parse_email(self, msg: email.message.Message) -> Dict[str, any]:
        """
        解析单封邮件

        Args:
            msg: 邮件消息对象

        Returns:
            解析后的邮件信息字典
        """
        # 获取头部信息
        subject = self._decode_header_value(msg.get('Subject', ''))
        from_addr = self._decode_header_value(msg.get('From', ''))
        to_addr = self._decode_header_value(msg.get('To', ''))
        cc_addr = self._decode_header_value(msg.get('Cc', ''))
        date_str = msg.get('Date', '')
        message_id = msg.get('Message-ID', '')

        # 解析日期
        try:
            date_obj = parsedate_to_datetime(date_str)
        except:
            date_obj = None

        # 获取正文
        body = self._get_email_body(msg)

        # 获取附件
        attachments = self._get_attachments(msg)

        return {
            'subject': subject,
            'from': from_addr,
            'to': to_addr,
            'cc': cc_addr,
            'date': date_obj,
            'date_str': date_str,
            'message_id': message_id,
            'body_plain': body['plain'],
            'body_html': body['html'],
            'attachments': attachments,
            'has_attachments': len(attachments) > 0,
        }

    def fetch_emails(
        self,
        folder: str = 'INBOX',
        limit: int = 10,
        since_date: str = None,
        search_criteria: str = None
    ) -> List[Dict[str, any]]:
        """
        获取邮件列表

        Args:
            folder: 文件夹名称（默认INBOX）
            limit: 最多获取多少封邮件
            since_date: 起始日期（格式：01-Jan-2023）
            search_criteria: 自定义搜索条件

        Returns:
            邮件信息列表
        """
        if not self.connected:
            if not self.connect():
                return []

        try:
            # 选择文件夹
            self.client.select(folder)
            print(f"[OK] 已选择文件夹: {folder}")

            # 构建搜索条件
            if search_criteria:
                criterion = search_criteria
            else:
                criterion = 'ALL'
                if since_date:
                    criterion = f'SINCE {since_date}'

            # 搜索邮件
            status, messages = self.client.search(None, criterion)
            if status != 'OK':
                print(f"[X] 搜索失败: {status}")
                return []

            email_ids = messages[0].split()
            total_count = len(email_ids)

            # 限制数量（获取最新的邮件）
            if limit > 0:
                email_ids = email_ids[-limit:]
            else:
                email_ids = email_ids

            print(f"[OK] 找到 {total_count} 封邮件，正在解析最新的 {len(email_ids)} 封...")

            emails = []
            for idx, email_id in enumerate(email_ids, 1):
                # 获取邮件
                status, msg_data = self.client.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue

                # 解析邮件
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                email_info = self.parse_email(msg)
                email_info['uid'] = email_id.decode()
                email_info['folder'] = folder

                emails.append(email_info)
                print(f"  [{idx}/{len(email_ids)}] {email_info['from']} - {email_info['subject'][:50]}...")

            return emails

        except Exception as e:
            print(f"[X] 获取邮件失败: {e}")
            return []

    def list_folders(self) -> List[str]:
        """
        列出所有文件夹

        Returns:
            文件夹列表
        """
        if not self.connected:
            if not self.connect():
                return []

        try:
            status, folders = self.client.list()
            if status != 'OK':
                return []

            folder_names = []
            for folder in folders:
                # 解析文件夹名称
                parts = folder.decode().split('"')
                if len(parts) >= 3:
                    folder_name = parts[-2] if parts[-2] else parts[3]
                    folder_names.append(folder_name)

            return folder_names

        except Exception as e:
            print(f"[X] 获取文件夹列表失败: {e}")
            return []

    def print_email_summary(self, email_info: Dict[str, any]):
        """
        打印邮件摘要

        Args:
            email_info: 邮件信息字典
        """
        print("\n" + "=" * 80)
        print(f"主题: {email_info['subject']}")
        print(f"发件人: {email_info['from']}")
        print(f"收件人: {email_info['to']}")
        if email_info['cc']:
            print(f"抄送: {email_info['cc']}")
        print(f"日期: {email_info['date_str']}")
        print(f"附件: {'是' if email_info['has_attachments'] else '否'}")

        if email_info['attachments']:
            print("\n附件列表:")
            for att in email_info['attachments']:
                print(f"  - {att['filename']} ({att['size']} bytes, {att['content_type']})")

        if email_info['body_plain']:
            print("\n正文内容:")
            print("-" * 80)
            # 显示前500字符
            body_preview = email_info['body_plain'][:500]
            if len(email_info['body_plain']) > 500:
                body_preview += "\n... (内容已截断)"
            print(body_preview)
            print("-" * 80)

        print("=" * 80)


def main():
    """主函数 - 示例用法"""
    # 加载.env文件（如果可用）
    if DOTENV_AVAILABLE:
        load_dotenv()

    # ==================== 配置信息 ====================
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS') or "chenguangming@gd.chinamobile.com"
    AUTH_CODE = os.getenv('AUTH_CODE') or "你的授权码"
    IMAP_SERVER = os.getenv('IMAP_SERVER') or "imap.chinamobile.com"  # 可选，自动检测
    # ================================================

    if AUTH_CODE == "你的授权码":
        print("错误: 请在.env文件中配置EMAIL_ADDRESS和AUTH_CODE")
        return

    print("=" * 80)
    print("IMAP 邮件客户端")
    print("=" * 80)

    # 创建客户端
    client = ImapEmailClient(EMAIL_ADDRESS, AUTH_CODE, IMAP_SERVER)

    try:
        # 连接
        if not client.connect():
            print("请检查邮箱地址和授权码是否正确")
            return

        # 列出所有文件夹
        print("\n文件夹列表:")
        folders = client.list_folders()
        for folder in folders:
            print(f"  - {folder}")

        # 获取最近的邮件（可以修改数量）
        emails = client.fetch_emails(folder='INBOX', limit=5)

        print(f"\n成功获取 {len(emails)} 封邮件\n")

        # 打印每封邮件的摘要
        for idx, email_info in enumerate(emails, 1):
            print(f"\n邮件 {idx}/{len(emails)}:")
            client.print_email_summary(email_info)

    finally:
        # 断开连接
        client.disconnect()


if __name__ == "__main__":
    main()
