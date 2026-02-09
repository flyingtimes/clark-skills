#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取邮件并保存到文件

支持命令行参数:
    --limit N    获取邮件数量 (默认: 5)
    --folder F   邮箱文件夹 (默认: INBOX)
"""

import sys
import io
import os
import argparse
from dotenv import load_dotenv
from email_client import ImapEmailClient

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 加载.env文件
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='获取邮件并保存到文件')
    parser.add_argument('--limit', type=int, default=5, help='获取邮件数量 (默认: 5)')
    parser.add_argument('--folder', type=str, default='INBOX', help='邮箱文件夹 (默认: INBOX)')
    args = parser.parse_args()

    EMAIL = os.getenv('EMAIL_ADDRESS')
    AUTH_CODE = os.getenv('AUTH_CODE')

    if not EMAIL or not AUTH_CODE:
        print("错误: 请在.env文件中配置EMAIL_ADDRESS和AUTH_CODE")
        sys.exit(1)

    client = ImapEmailClient(EMAIL, AUTH_CODE)

    try:
        if not client.connect():
            print("连接失败")
            sys.exit(1)

        # 获取邮件
        emails = client.fetch_emails(folder=args.folder, limit=args.limit)

        # 保存到文件
        with open('emails_result.txt', 'w', encoding='utf-8') as f:
            f.write(f"共获取 {len(emails)} 封邮件\n")
            f.write("=" * 80 + "\n\n")

            for i, email_info in enumerate(emails, 1):
                f.write(f"邮件 #{i}\n")
                f.write("=" * 80 + "\n")
                f.write(f"发件人: {email_info['from']}\n")
                f.write(f"标题: {email_info['subject']}\n")
                f.write(f"日期: {email_info['date_str']}\n")
                f.write(f"收件人: {email_info['to']}\n")

                if email_info['cc']:
                    f.write(f"抄送: {email_info['cc']}\n")

                f.write(f"附件: {'是' if email_info['has_attachments'] else '否'}\n")

                if email_info['attachments']:
                    f.write("\n附件列表:\n")
                    for att in email_info['attachments']:
                        f.write(f"  - {att['filename']} ({att['size']} bytes, {att['content_type']})\n")

                if email_info['body_plain']:
                    f.write("\n正文内容:\n")
                    f.write("-" * 80 + "\n")
                    f.write(email_info['body_plain'])
                    f.write("\n" + "-" * 80 + "\n")

                f.write("\n\n")

        print(f"结果已保存到 emails_result.txt")

    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
