#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件数据库管理模块
使用 SQLite 存储邮件信息和分类标签
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime


class EmailDatabase:
    """邮件数据库管理类"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认在 scripts 目录下
        """
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(script_dir, 'emails.db')

        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> bool:
        """连接到数据库并创建表结构"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self._create_tables()
            return True
        except Exception as e:
            print(f"[X] 数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _create_tables(self):
        """创建数据库表结构"""
        cursor = self.conn.cursor()

        # 邮件主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                uid TEXT,
                folder TEXT DEFAULT 'INBOX',
                subject TEXT,
                from_addr TEXT,
                to_addr TEXT,
                cc_addr TEXT,
                date_sent TEXT,
                date_received TEXT DEFAULT CURRENT_TIMESTAMP,
                body_plain TEXT,
                body_html TEXT,
                has_attachments INTEGER DEFAULT 0,
                processed INTEGER DEFAULT 0,
                category TEXT,
                urgency TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 附件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                size INTEGER,
                content_type TEXT,
                FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_message_id
            ON emails(message_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_category
            ON emails(category)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_urgency
            ON emails(urgency)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_processed
            ON emails(processed)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date_sent
            ON emails(date_sent DESC)
        ''')

        self.conn.commit()

    def email_exists(self, message_id: str) -> bool:
        """
        检查邮件是否已存在

        Args:
            message_id: 邮件的 Message-ID 头部

        Returns:
            邮件是否已存在
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM emails WHERE message_id = ?', (message_id,))
        return cursor.fetchone() is not None

    def add_email(self, email_info: Dict[str, Any]) -> int:
        """
        添加一封邮件到数据库

        Args:
            email_info: 邮件信息字典

        Returns:
            插入的邮件ID，如果已存在则返回-1
        """
        # 检查是否已存在
        message_id = email_info.get('message_id', '')
        if not message_id or self.email_exists(message_id):
            return -1

        cursor = self.conn.cursor()

        # 插入邮件
        cursor.execute('''
            INSERT INTO emails (
                message_id, uid, folder, subject, from_addr, to_addr, cc_addr,
                date_sent, body_plain, body_html, has_attachments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_id,
            email_info.get('uid', ''),
            email_info.get('folder', 'INBOX'),
            email_info.get('subject', ''),
            email_info.get('from', ''),
            email_info.get('to', ''),
            email_info.get('cc', ''),
            email_info.get('date_str', ''),
            email_info.get('body_plain'),
            email_info.get('body_html'),
            1 if email_info.get('has_attachments') else 0
        ))

        email_id = cursor.lastrowid

        # 插入附件信息
        for att in email_info.get('attachments', []):
            cursor.execute('''
                INSERT INTO attachments (email_id, filename, size, content_type)
                VALUES (?, ?, ?, ?)
            ''', (
                email_id,
                att.get('filename', ''),
                att.get('size', 0),
                att.get('content_type', '')
            ))

        self.conn.commit()
        return email_id

    def update_email_classification(self, message_id: str, category: str, urgency: str) -> bool:
        """
        更新邮件分类信息

        Args:
            message_id: 邮件的 Message-ID
            category: 分类 (task/notification)
            urgency: 紧急程度 (urgent/normal)

        Returns:
            是否更新成功
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE emails
            SET category = ?, urgency = ?, processed = 1, updated_at = CURRENT_TIMESTAMP
            WHERE message_id = ?
        ''', (category, urgency, message_id))

        self.conn.commit()
        return cursor.rowcount > 0

    def get_unprocessed_emails(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取未分类的邮件

        Args:
            limit: 最多获取数量

        Returns:
            未分类邮件列表
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM emails
            WHERE processed = 0
            ORDER BY date_sent DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_urgent_unprocessed_emails(self) -> List[Dict[str, Any]]:
        """
        获取紧急且未处理的邮件（用于发送综述）

        Returns:
            紧急邮件列表
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM emails
            WHERE processed = 1 AND urgency = 'urgent'
            ORDER BY date_sent DESC
        ''')

        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_emails(self, limit: int = None, category: str = None,
                       urgency: str = None) -> List[Dict[str, Any]]:
        """
        获取所有邮件（可选筛选条件）

        Args:
            limit: 最多获取数量
            category: 分类筛选
            urgency: 紧急程度筛选

        Returns:
            邮件列表
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM emails WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)

        if urgency:
            query += ' AND urgency = ?'
            params.append(urgency)

        query += ' ORDER BY date_sent DESC'

        if limit:
            query += ' LIMIT ?'
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_email_attachments(self, email_id: int) -> List[Dict[str, Any]]:
        """
        获取邮件的附件列表

        Args:
            email_id: 邮件ID

        Returns:
            附件列表
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM attachments WHERE email_id = ?', (email_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        cursor = self.conn.cursor()

        stats = {}

        # 总邮件数
        cursor.execute('SELECT COUNT(*) as count FROM emails')
        stats['total_emails'] = cursor.fetchone()['count']

        # 未处理邮件数
        cursor.execute('SELECT COUNT(*) as count FROM emails WHERE processed = 0')
        stats['unprocessed'] = cursor.fetchone()['count']

        # 已处理邮件数
        cursor.execute('SELECT COUNT(*) as count FROM emails WHERE processed = 1')
        stats['processed'] = cursor.fetchone()['count']

        # 按分类统计
        cursor.execute('''
            SELECT category, COUNT(*) as count
            FROM emails
            WHERE category IS NOT NULL
            GROUP BY category
        ''')
        stats['by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}

        # 按紧急程度统计
        cursor.execute('''
            SELECT urgency, COUNT(*) as count
            FROM emails
            WHERE urgency IS NOT NULL
            GROUP BY urgency
        ''')
        stats['by_urgency'] = {row['urgency']: row['count'] for row in cursor.fetchall()}

        # 最新邮件时间
        cursor.execute('SELECT MAX(date_sent) as latest FROM emails')
        stats['latest_date'] = cursor.fetchone()['latest']

        return stats

    def mark_summary_sent(self, email_ids: List[int]):
        """
        标记邮件已发送综述（可选功能）

        Args:
            email_ids: 邮件ID列表
        """
        if not email_ids:
            return

        cursor = self.conn.cursor()
        placeholders = ','.join('?' * len(email_ids))
        cursor.execute(f'''
            UPDATE emails
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', email_ids)
        self.conn.commit()


def main():
    """测试函数"""
    db = EmailDatabase()

    if not db.connect():
        print("数据库连接失败")
        return

    try:
        # 显示统计信息
        stats = db.get_stats()
        print("\n=== 数据库统计 ===")
        print(f"总邮件数: {stats['total_emails']}")
        print(f"已处理: {stats['processed']}")
        print(f"未处理: {stats['unprocessed']}")
        print(f"按分类: {stats.get('by_category', {})}")
        print(f"按紧急程度: {stats.get('by_urgency', {})}")
        print(f"最新邮件日期: {stats.get('latest_date', '无')}")

        # 获取最近邮件
        emails = db.get_all_emails(limit=5)
        print(f"\n=== 最近5封邮件 ===")
        for email in emails:
            status = f"[{email.get('category', 'N/A')}/{email.get('urgency', 'N/A')}]"
            print(f"  {status} {email['subject'][:50]}... - {email['from_addr']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
