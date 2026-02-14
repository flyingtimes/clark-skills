#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件同步脚本
从 IMAP 服务器获取新邮件并存储到数据库
支持从 keyring 读取凭据
"""

import sys
import os
import argparse

# 添加父目录到路径以导入 email_client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../email/scripts'))
from email_client import ImapEmailClient, KEYRING_AVAILABLE
from db_manager import EmailDatabase

# 设置标准输出为UTF-8编码
if hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def sync_emails(limit: int = 50, folder: str = 'INBOX', email_address: str = None, auth_code: str = None) -> dict:
    """
    同步邮件到数据库

    Args:
        limit: 获取邮件数量
        folder: 邮箱文件夹
        email_address: 邮箱地址（可选）
        auth_code: 授权码（可选）

    Returns:
        同步结果统计
    """
    # 从 keyring 或环境变量获取凭据
    EMAIL, AUTH_CODE, imap_server, imap_port = ImapEmailClient.get_credentials(email_address, auth_code)

    if not EMAIL or not AUTH_CODE:
        error_msg = '请配置邮箱凭据'
        if KEYRING_AVAILABLE:
            error_msg += '\n  命令行: python sync.py --email your@email.com --auth-code YOUR_CODE'
            error_msg += '\n  或使用 keyring 设置凭据'
        else:
            error_msg += '\n  命令行: python sync.py --email your@email.com --auth-code YOUR_CODE'
        return {'success': False, 'error': error_msg}

    # 连接数据库
    db = EmailDatabase()
    if not db.connect():
        return {'success': False, 'error': '数据库连接失败'}

    # 连接邮箱
    client = ImapEmailClient(EMAIL, AUTH_CODE, imap_server, imap_port)
    if not client.connect():
        db.close()
        return {'success': False, 'error': '邮箱连接失败'}

    try:
        # 获取邮件
        emails = client.fetch_emails(folder=folder, limit=limit)

        new_count = 0
        duplicate_count = 0
        error_count = 0

        for email_info in emails:
            try:
                email_id = db.add_email(email_info)
                if email_id > 0:
                    new_count += 1
                else:
                    duplicate_count += 1
            except Exception as e:
                error_count += 1
                print(f"[X] 添加邮件失败: {e}")

        return {
            'success': True,
            'total': len(emails),
            'new': new_count,
            'duplicate': duplicate_count,
            'error': error_count
        }

    finally:
        client.disconnect()
        db.close()


def main():
    parser = argparse.ArgumentParser(description='同步邮件到数据库')
    parser.add_argument('--limit', type=int, default=50, help='获取邮件数量 (默认: 50)')
    parser.add_argument('--folder', type=str, default='INBOX', help='邮箱文件夹 (默认: INBOX)')
    parser.add_argument('--email', help='发件人邮箱地址')
    parser.add_argument('--auth-code', help='IMAP授权码')
    args = parser.parse_args()

    result = sync_emails(limit=args.limit, folder=args.folder, email_address=args.email, auth_code=args.auth_code)

    if result['success']:
        print(f"\n[OK] 同步完成")
        print(f"  总获取: {result['total']} 封")
        print(f"  新邮件: {result['new']} 封")
        print(f"  已存在: {result['duplicate']} 封")
        if result['error'] > 0:
            print(f"  错误: {result['error']} 封")
    else:
        print(f"\n[X] 同步失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
