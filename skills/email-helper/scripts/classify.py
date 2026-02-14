#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件AI分类脚本
使用本地 Ollama 模型对未分类邮件进行分类
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime
from db_manager import EmailDatabase

# 设置标准输出为UTF-8编码
if hasattr(sys.stdout, 'buffer'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


class OllamaClassifier:
    """Ollama 分类器"""

    def __init__(self, model: str = "glm-4.7-flash:bf16"):
        """
        初始化分类器

        Args:
            model: Ollama 模型名称
        """
        self.model = model
        self.base_url = os.getenv('OLLAMA_HOST', 'http://localhost:11434')

    def _call_ollama(self, prompt: str) -> str:
        """
        调用 Ollama API

        Args:
            prompt: 提示词

        Returns:
            模型响应文本
        """
        import urllib.request
        import urllib.error

        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 50
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('response', '').strip()
        except urllib.error.URLError as e:
            # 如果API调用失败，尝试使用命令行
            return self._call_ollama_cli(prompt)
        except Exception as e:
            print(f"[!] API调用失败，尝试使用命令行: {e}")
            return self._call_ollama_cli(prompt)

    def _call_ollama_cli(self, prompt: str) -> str:
        """
        使用命令行调用 Ollama

        Args:
            prompt: 提示词

        Returns:
            模型响应文本
        """
        try:
            result = subprocess.run(
                ['ollama', 'run', self.model, prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            return result.stdout.strip()
        except FileNotFoundError:
            return ""
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            print(f"[X] 命令行调用失败: {e}")
            return ""

    def classify_email(self, subject: str, body: str) -> tuple:
        """
        对单封邮件进行分类

        Args:
            subject: 邮件标题
            body: 邮件正文

        Returns:
            (category, urgency) 分类和紧急程度
        """
        # 限制正文长度
        body_preview = body[:1000] if body else ""

        prompt = f"""请分析以下邮件，判断其类型和紧急程度。

邮件标题: {subject}
邮件正文: {body_preview}

请严格按照以下格式回答，不要包含其他内容：
类型:task 或 notification
紧急:urgent 或 normal

判断标准：
- task: 需要执行的任务、工作安排、会议邀请、待办事项等
- notification: 通知、公告、周报、日报、信息告知等
- urgent: 包含"紧急"、"重要"、"ASAP"、"尽快"等关键词，或来自上级的直接指令
- normal: 常规邮件，无明显紧急标记

回答格式：
类型: [task/notification]
紧急: [urgent/normal]
"""

        response = self._call_ollama(prompt)

        # 解析响应
        category = None
        urgency = None

        for line in response.split('\n'):
            line = line.strip().lower()
            if '类型:' in line or 'type:' in line or 'category:' in line:
                if 'task' in line:
                    category = 'task'
                elif 'notification' in line:
                    category = 'notification'
            if '紧急:' in line or 'urgency:' in line or 'priority:' in line:
                if 'urgent' in line or '紧急' in line:
                    urgency = 'urgent'
                elif 'normal' in line or '普通' in line:
                    urgency = 'normal'

        # 默认值
        if not category:
            category = 'notification'
        if not urgency:
            urgency = 'normal'

        return category, urgency

    def test_connection(self) -> bool:
        """
        测试与 Ollama 的连接

        Returns:
            是否连接成功
        """
        try:
            # 殳先尝试 API
            import urllib.request
            import urllib.error

            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as response:
                return True
        except:
            # 尝试命令行
            try:
                result = subprocess.run(
                    ['ollama', 'list'],
                    capture_output=True,
                    timeout=10
                )
                return result.returncode == 0
            except:
                return False


def classify_emails(limit: int = 50, model: str = "glm-4.7-flash:bf16",
                    verbose: bool = True) -> dict:
    """
    对未分类邮件进行AI分类

    Args:
        limit: 最多处理数量
        model: Ollama 模型名称
        verbose: 是否显示详细输出

    Returns:
        处理结果统计
    """
    db = EmailDatabase()
    if not db.connect():
        return {'success': False, 'error': '数据库连接失败'}

    try:
        # 获取未分类邮件
        unprocessed = db.get_unprocessed_emails(limit=limit)

        if not unprocessed:
            return {
                'success': True,
                'total': 0,
                'processed': 0,
                'skipped': 0,
                'message': '没有需要分类的邮件'
            }

        # 初始化分类器
        classifier = OllamaClassifier(model=model)

        if verbose:
            print(f"\n[OK] 找到 {len(unprocessed)} 封未分类邮件")
            print(f"[OK] 使用模型: {model}")

        # 测试连接
        if not classifier.test_connection():
            return {
                'success': False,
                'error': '无法连接到 Ollama，请确保服务已启动'
            }

        processed = 0
        failed = 0

        for email in unprocessed:
            message_id = email['message_id']
            subject = email.get('subject', '')
            body = email.get('body_plain', '')

            if verbose:
                print(f"\n[{processed+1}/{len(unprocessed)}] 正在处理: {subject[:50]}...")

            # 调用AI分类
            try:
                category, urgency = classifier.classify_email(subject, body)

                # 更新数据库
                if db.update_email_classification(message_id, category, urgency):
                    processed += 1
                    if verbose:
                        print(f"      -> 分类: {category}, 紧急程度: {urgency}")
                else:
                    failed += 1
                    if verbose:
                        print(f"      -> 更新失败")

            except Exception as e:
                failed += 1
                if verbose:
                    print(f"      -> 分类失败: {e}")

        return {
            'success': True,
            'total': len(unprocessed),
            'processed': processed,
            'failed': failed
        }

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='AI分类邮件')
    parser.add_argument('--limit', '-n', type=int, default=50,
                        help='最多处理数量 (默认: 50)')
    parser.add_argument('--model', '-m', type=str, default='glm-4.7-flash:bf16',
                        help='Ollama 模型名称 (默认: glm-4.7-flash:bf16)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='静默模式，减少输出')
    args = parser.parse_args()

    result = classify_emails(
        limit=args.limit,
        model=args.model,
        verbose=not args.quiet
    )

    if result['success']:
        print(f"\n[OK] 分类完成")
        print(f"  找到: {result['total']} 封未分类邮件")
        print(f"  已处理: {result.get('processed', 0)} 封")
        if result.get('failed', 0) > 0:
            print(f"  失败: {result['failed']} 封")
        if 'message' in result:
            print(f"  {result['message']}")
    else:
        print(f"\n[X] 分类失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
