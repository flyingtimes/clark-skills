#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件综述生成脚本
对新处理的紧急邮件进行综述并发送给自己
"""

import sys
import os
import argparse
import subprocess
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
            return dt.strftime('%Y-%m-%d %H:%M')
        return str(dt)[:16]
    except:
        return date_str[:16]


def truncate_text(text: str, max_len: int = 100) -> str:
    """截断文本"""
    if not text:
        return ''
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + '...'


def generate_summary(urgent_only: bool = True, limit: int = 20) -> dict:
    """
    生成邮件综述并发送

    Args:
        urgent_only: 是否只包含紧急邮件
        limit: 最多包含邮件数量

    Returns:
        结果统计
    """
    db = EmailDatabase()
    if not db.connect():
        return {'success': False, 'error': '数据库连接失败'}

    try:
        # 获取紧急邮件
        if urgent_only:
            emails = db.get_urgent_unprocessed_emails()[:limit]
        else:
            # 获取最近已处理的邮件
            cursor = db.conn.cursor()
            cursor.execute('''
                SELECT * FROM emails
                WHERE processed = 1
                ORDER BY date_sent DESC
                LIMIT ?
            ''', (limit,))
            emails = [dict(row) for row in cursor.fetchall()]

        if not emails:
            return {
                'success': True,
                'sent': False,
                'message': '没有需要发送综述的邮件'
            }

        # 构建邮件内容
        subject = f"邮件综述 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        body_lines = [
            f"<h2>邮件处理综述</h2>",
            f"<p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p>共 <strong>{len(emails)}</strong> 封邮件</p>",
            "<hr>",
            ""
        ]

        # 按分类分组
        tasks = [e for e in emails if e.get('category') == 'task']
        notifications = [e for e in emails if e.get('category') == 'notification']
        others = [e for e in emails if e.get('category') not in ['task', 'notification']]

        if tasks:
            body_lines.append("<h3>📋 任务类邮件</h3>")
            for email in tasks:
                urgency_mark = "🔴" if email.get('urgency') == 'urgent' else "🟢"
                body_lines.append(f"<p>{urgency_mark} <strong>{email['subject']}</strong></p>")
                body_lines.append(f"<p>发件人: {email.get('from_addr', 'N/A')}</p>")
                body_lines.append(f"<p>时间: {format_date(email.get('date_sent', ''))}</p>")
                body = email.get('body_plain', '')
                if body:
                    body_lines.append(f"<p>摘要: {truncate_text(body, 200)}</p>")
                body_lines.append("")

        if notifications:
            body_lines.append("<h3>📢 通知类邮件</h3>")
            for email in notifications:
                urgency_mark = "🔴" if email.get('urgency') == 'urgent' else "🟢"
                body_lines.append(f"<p>{urgency_mark} <strong>{email['subject']}</strong></p>")
                body_lines.append(f"<p>发件人: {email.get('from_addr', 'N/A')}</p>")
                body_lines.append(f"<p>时间: {format_date(email.get('date_sent', ''))}</p>")
                body_lines.append("")

        if others:
            body_lines.append("<h3>📂 其他邮件</h3>")
            for email in others:
                body_lines.append(f"<p>• {email['subject']} - {email.get('from_addr', 'N/A')}</p>")
            body_lines.append("")

        body = '\n'.join(body_lines)

        # 添加页脚
        body += f"<hr><p><small>由 email-helper 自动生成</small></p>"

        # 调用 send-email 脚本发送
        send_email_script = os.path.join(
            os.path.dirname(__file__), '../../send-email/scripts/send_email.py'
        )

        if not os.path.exists(send_email_script):
            return {
                'success': False,
                'error': f'找不到 send-email 脚本: {send_email_script}'
            }

        try:
            # 使用 subprocess 调用 send_email.py
            result = subprocess.run(
                ['python3', send_email_script, body],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # 标记已发送
                email_ids = [e['id'] for e in emails]
                db.mark_summary_sent(email_ids)

                return {
                    'success': True,
                    'sent': True,
                    'count': len(emails),
                    'message': result.stdout.strip()
                }
            else:
                return {
                    'success': False,
                    'sent': False,
                    'error': result.stderr.strip() or result.stdout.strip()
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'sent': False,
                'error': '发送邮件超时'
            }
        except Exception as e:
            return {
                'success': False,
                'sent': False,
                'error': str(e)
            }

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='生成邮件综述并发送')
    parser.add_argument('--all', '-a', action='store_true',
                        help='包含所有已处理邮件，不限于紧急')
    parser.add_argument('--limit', '-n', type=int, default=20,
                        help='最多包含邮件数量 (默认: 20)')
    args = parser.parse_args()

    result = generate_summary(
        urgent_only=not args.all,
        limit=args.limit
    )

    if result['success']:
        if result.get('sent'):
            print(f"\n[OK] 综述已发送")
            print(f"  包含邮件: {result.get('count', 0)} 封")
        else:
            print(f"\n[OK] {result.get('message', '操作完成')}")
    else:
        print(f"\n[X] 操作失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
