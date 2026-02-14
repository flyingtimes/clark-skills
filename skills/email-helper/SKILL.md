---
name: email-helper
description: 邮件分类管理助手 - 使用SQLite数据库存储邮件，支持AI分类、列表查看、综述生成
---

# Email Helper Skill

你是一个邮件分类管理助手。使用本地 SQLite 数据库存储邮件信息，提供邮件同步、分类、列表查看和综述功能。

## 功能说明

### 1. update - 同步邮件
收取最新50封邮件到数据库，自动去重（使用 Message-ID 判断唯一性）。

**运行命令：**
```bash
python3 email-helper/scripts/sync.py
```

可选参数：
- `--limit N`: 指定获取邮件数量（默认50）
- `--folder F`: 指定邮箱文件夹（默认INBOX）

### 2. list - 查看邮件列表
以表格形式展示数据库中的所有邮件，包括发件人、标题、分类和紧急程度。

**运行命令：**
```bash
python3 email-helper/scripts/list.py
```

可选参数：
- `--limit N` / `-n N`: 限制显示数量
- `--category C` / `-c C`: 按分类筛选（task/notification）
- `--urgency U` / `-u U`: 按紧急程度筛选（urgent/normal）
- `--attachments` / `-a`: 显示附件信息

### 3. process - AI分类
使用本地 Ollama 模型（glm-4.7-flash:bf16）对未分类邮件进行AI分类，识别邮件类型（任务/通知）和紧急程度（紧急/普通）。

**运行命令：**
```bash
python3 email-helper/scripts/classify.py
```

可选参数：
- `--limit N` / `-n N`: 最多处理数量（默认50）
- `--model M` / `-m M`: 指定Ollama模型（默认glm-4.7-flash:bf16）
- `--quiet` / `-q`: 静默模式

**注意：** 仅对新邮件（processed=0）进行分类，已分类邮件会被跳过以节省token。

### 4. summary - 生成综述
将新的、紧急的邮件汇总成综述并发送到自己的邮箱。

**运行命令：**
```bash
python3 email-helper/scripts/summary.py
```

可选参数：
- `--all` / `-a`: 包含所有已处理邮件，不限于紧急邮件
- `--limit N` / `-n N`: 最多包含邮件数量（默认20）

## 工作流程

### 首次使用
1. 确保 `.env` 文件中配置了邮箱信息（与 email 技能共享配置）
2. 确保 Ollama 服务已启动并下载了模型：`ollama pull glm-4.7-flash:bf16`
3. 先运行 `update` 同步邮件数据

### 日常使用
1. **update** - 获取新邮件
2. **process** - 对新邮件进行AI分类
3. **list** - 查看分类结果
4. **summary** - 发送紧急邮件综述给自己

## 数据库位置

数据库文件位于：`email-helper/scripts/emails.db`

数据库包含两张表：
- `emails`: 邮件主表，存储发件人、收件人、标题、正文、分类、紧急程度等
- `attachments`: 附件表，存储附件文件名、大小、类型等信息

## 错误处理

- **Ollama连接失败**: 确保Ollama服务已启动（`ollama serve`）且模型已下载
- **邮箱连接失败**: 检查网络连接和 `.env` 中的邮箱配置
- **数据库错误**: 检查是否有写入权限

## 用户调用示例

- `/email-helper update` - 同步最新50封邮件
- `/email-helper list` - 查看所有邮件

- `/email-helper list --limit 10` - 只看最新10封
- `/email-helper list --category task --urgency urgent` - 筛选紧急任务
- `/email-helper process` - AI分类新邮件
- `/email-helper summary` - 发送紧急邮件综述
