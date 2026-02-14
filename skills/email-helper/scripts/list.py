#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件列表脚本
以表格形式展示数据库中的邮件信息
"""

import sys
import os
import argparse
from datetime import datetime
from db_manager import EmailDatabase

# 设置标准输出为UTF-8编码
if hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def format_date(date_str: str) -> str:
    """格式化日期字符串"""
    if not date_str:
        return 'N/A'
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if 'T' in date_str else date_str
        if isinstance(dt, datetime):
            return dt.strftime('%m-%d %H:%M')
        return str(dt)[:16]
    except:
        return date_str[:16]


def truncate_text(text: str, max_len: int = 30) -> str:
    """截断文本"""
    if not text:
        return ''
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + '...'


def get_body_summary(body: str, max_len: int = 60) -> str:
    """获取正文摘要"""
    if not body:
        return ''
    # 移除换行和多余空格，取前N个字符
    clean_body = body.replace('\n', ' ').replace('\r', ' ').strip()
    # 按空格分词，取前几个词
    words = clean_body.split()[:8]  # 取前8个词
    summary = ' '.join(words)
    if len(clean_body) > len(summary):
        summary += '...'
    return truncate_text(summary, max_len)


def print_table(emails: list, show_attachments: bool = False, db=None):
    """
    打印邮件表格

    Args:
        emails: 邮件列表
        show_attachments: 是否显示附件信息
        db: 数据库连接（用于获取附件详情）
    """
    if not emails:
        print("\n暂无邮件数据")
        return

    # 表头
    print(f"\n{'ID':<5} {'日期':<10} {'发件人':<18} {'标题':<30} {'摘要':<60} {'分类':<8} {'紧急':<6}")
    print("=" * 145)

    for email in emails:
        email_id = email.get('id', 'N/A')
        date_str = format_date(email.get('date_sent', ''))
        from_addr = truncate_text(email.get('from_addr', ''), 18)
        subject = truncate_text(email.get('subject', ''), 30)
        body = email.get('body_plain', '')
        summary = get_body_summary(body, 60)
        category = email.get('category') or '未分类'
        urgency = email.get('urgency') or '-'

        print(f"{email_id:<5} {date_str:<10} {from_addr:<18} {subject:<30} {summary:<60} {category:<8} {urgency:<6}")

        # 显示附件
        if show_attachments and email.get('has_attachments'):
            print(f"      附件: {email.get('attachment_count', 0)} 个")

    print("=" * 145)
    print(f"共 {len(emails)} 封邮件\n")


def print_email_details(emails: list, db):
    """
    打印每封邮件的详细信息

    Args:
        emails: 邮件列表
        db: 数据库连接
    """
    for email in emails:
        email_id = email.get('id')
        print(f"\n{'='*80}")
        print(f"邮件ID: {email_id}")
        print(f"{'='*80}")

        # 基本信息
        print(f"  日期:       {email.get('date_sent', 'N/A')}")
        print(f"  发件人:     {email.get('from_addr', 'N/A')}")
        print(f"  收件人:     {email.get('to_addr', 'N/A')}")
        if email.get('cc_addr'):
            print(f"  抄送:       {email.get('cc_addr', '')}")

        # 分类信息
        category = email.get('category') or '未分类'
        urgency = email.get('urgency') or '-'
        print(f"  分类:       {category}")
        print(f"  紧急程度:   {urgency}")

        # 主题
        print(f"\n  主题:")
        print(f"    {email.get('subject', 'N/A')}")

        # 正文（纯文本）
        body = email.get('body_plain', '')
        if body:
            # 限制显示长度，避免输出过长
            max_body_len = 500
            if len(body) > max_body_len:
                body = body[:max_body_len] + f"\n    ... (已截断，共{len(body)}字符)"
            print(f"\n  正文:")
            for line in body.split('\n'):
                print(f"    {line}")

        # 附件信息
        if email.get('has_attachments'):
            attachments = db.get_email_attachments(email_id)
            if attachments:
                print(f"\n  附件 ({len(attachments)}个):")
                for att in attachments:
                    size_kb = att.get('size', 0) / 1024
                    print(f"    - {att.get('filename', 'unknown')}")
                    print(f"      大小: {size_kb:.1f} KB, 类型: {att.get('content_type', 'unknown')}")

        print()


def list_emails(limit: int = None, category: str = None,
                urgency: str = None, show_attachments: bool = False, no_details: bool = False) -> dict:
    """
    列出邮件

    Args:
        limit: 最多显示数量
        category: 分类筛选
        urgency: 紧急程度筛选
        show_attachments: 是否显示附件信息
        no_details: 不显示详细信息（仅显示表格）

    Returns:
        结果统计
    """
    db = EmailDatabase()
    if not db.connect():
        return {'success': False, 'error': '数据库连接失败'}

    try:
        # 获取邮件
        emails = db.get_all_emails(limit=limit, category=category, urgency=urgency)

        # 获取统计信息
        stats = db.get_stats()

        # 显示统计信息
        print("\n=== 数据库统计 ===")
        print(f"总邮件数: {stats['total_emails']}")
        print(f"已处理: {stats['processed']}")
        print(f"未处理: {stats['unprocessed']}")

        if stats.get('by_category'):
            print(f"按分类: {stats['by_category']}")
        if stats.get('by_urgency'):
            print(f"按紧急程度: {stats['by_urgency']}")

        # 显示邮件表格
        print_table(emails, show_attachments, db)

        # 显示每封邮件的详细信息（除非指定不显示）
        if not no_details and emails:
            print_email_details(emails, db)

        return {
            'success': True,
            'count': len(emails),
            'stats': stats
        }

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='列出邮件')
    parser.add_argument('--limit', '-n', type=int, default=None, help='最多显示数量 (默认: 全部)')
    parser.add_argument('--category', '-c', type=str, default=None,
                        choices=['task', 'notification'], help='按分类筛选')
    parser.add_argument('--urgency', '-u', type=str, default=None,
                        choices=['urgent', 'normal'], help='按紧急程度筛选')
    parser.add_argument('--attachments', '-a', action='store_true', help='显示附件信息')
    parser.add_argument('--no-details', action='store_true', help='不显示详细信息（仅显示表格）')
    args = parser.parse_args()

    result = list_emails(
        limit=args.limit,
        category=args.category,
        urgency=args.urgency,
        show_attachments=args.attachments,
        no_details=args.no_details
    )

    if not result['success']:
        print(f"\n[X] 操作失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
