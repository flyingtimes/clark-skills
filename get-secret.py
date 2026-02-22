#!/usr/bin/env python3
"""
Claude Code 多密钥安全获取脚本
自动判断操作系统，支持 macOS (Keychain) + Windows (Credential Manager)
密钥不存在时，会提示用户输入并自动存储到 keyring
"""

import sys
import platform
import keyring
from getpass import getpass  # 用于安全输入（不回显）

def detect_os():
    sys_name = platform.system().lower()
    if "darwin" in sys_name:
        return "macOS"
    elif "windows" in sys_name or "win" in sys_name:
        return "Windows"
    else:
        return "Other"

def get_or_prompt_secret(service: str) -> str:
    secret = keyring.get_password("claude-secrets", service)
    
    if secret:
        return secret
    
    # 密钥不存在 → 提示输入
    os_type = detect_os()
    print(f"⚠️  未找到密钥：{service}", file=sys.stderr)
    print(f"当前系统：{os_type}", file=sys.stderr)
    print(f"请在下方输入 {service} 的值（输入不会显示在屏幕上）：", file=sys.stderr)
    
    try:
        new_secret = getpass(prompt="> ").strip()
        if not new_secret:
            print("输入为空，已取消。", file=sys.stderr)
            sys.exit(1)
        
        # 存入 keyring
        keyring.set_password("claude-secrets", service, new_secret)
        print(f"✓ 已将 {service} 安全存储到系统密钥管理器", file=sys.stderr)
        
        return new_secret
    
    except KeyboardInterrupt:
        print("\n已取消输入。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"存储失败：{e}", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("用法：", file=sys.stderr)
        print("  python get-secret.py <service>", file=sys.stderr)
        print("  支持的服务：email-token / glm-code / 你后续添加的任意服务名", file=sys.stderr)
        sys.exit(1)

    service = sys.argv[1].strip()
    secret = get_or_prompt_secret(service)
    
    # 只输出纯密钥值（供 Claude 或其他程序使用）
    print(secret)


if __name__ == "__main__":
    main()