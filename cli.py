"""CLI 入口"""
#!/usr/bin/env python3
"""
Writer_cli - 网文撰写 CLI Agent

用法:
    python cli.py generate --vol VOL_1 --chapter 1
    python cli.py generate --vol VOL_1 --chapter 1 --type climax
    python cli.py status
    python cli.py list-pending
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config import get_project_root
from core.scheduler import get_scheduler
from agents.orchestrator import get_orchestrator


def cmd_generate(args):
    """生成章节"""
    vol = args.vol
    chapter = args.chapter
    chapter_type = args.type or "normal"

    print(f"开始生成 {vol} Chapter {chapter} (类型: {chapter_type})")

    # 加载 env 文件中的环境变量
    env_file = Path(__file__).parent.parent / "env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    key, value = line[7:].split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # 初始化 LLM 客户端
    from core.generator import create_llm_client
    llm_client = create_llm_client()
    print(f"[Info] 使用 LLM 客户端: {type(llm_client).__name__}")

    # 获取主控 Agent
    orchestrator = get_orchestrator(llm_client)

    # 执行章节循环
    success, message = orchestrator.run_chapter_loop(vol, chapter, chapter_type)

    if success:
        print(f"[成功] {message}")
    else:
        print(f"[失败] {message}")
        sys.exit(1)


def cmd_status(args):
    """查看状态"""
    scheduler = get_scheduler()
    schedule = scheduler.load_schedule()

    print("# 当前状态")
    print()

    current = schedule.get("current_task")
    if current:
        print(f"当前任务: {current.get('volume', 'N/A')} Chapter {current.get('chapter', 'N/A')}")
        print(f"状态: {current.get('status', 'N/A')}")
    else:
        print("无当前任务")


def cmd_list_pending(args):
    """列出待执行任务"""
    scheduler = get_scheduler()
    schedule = scheduler.load_schedule()

    print("# 待执行任务")
    print()
    print("暂无待执行任务")


def cmd_init(args):
    """初始化项目结构"""
    root = get_project_root()

    # 创建必要目录
    dirs = ["chapters", "mailbox/outbox", "mailbox/inbox"]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # 创建默认配置文件
    configs = [
        ("CLAUDE.md", "# 全局硬规则锁\n\n## 世界观物理规则\n[在此填写]\n"),
        ("MEMORY.md", "# 动态伏笔状态机\n\n## 伏笔条目\n"),
        ("OUTLINE.md", "# 小说大纲\n\n## 总纲\n[在此填写]\n"),
        ("SCHEDULE.md", "# 任务调度队列\n\n## 当前任务\n- volume: VOL_1\n- chapter: 1\n- status: READY\n"),
    ]

    for filename, content in configs:
        filepath = root / filename
        if not filepath.exists():
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    print("项目初始化完成")


def main():
    parser = argparse.ArgumentParser(
        description="Writer_cli - 网文撰写 CLI Agent"
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成章节")
    gen_parser.add_argument("--vol", required=True, help="卷名，如 VOL_1")
    gen_parser.add_argument("--chapter", type=int, required=True, help="章节号")
    gen_parser.add_argument("--type", choices=["normal", "climax", "transition"],
                            help="章节类型")
    gen_parser.set_defaults(func=cmd_generate)

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看状态")
    status_parser.set_defaults(func=cmd_status)

    # list-pending 命令
    list_parser = subparsers.add_parser("list-pending", help="列出待执行任务")
    list_parser.set_defaults(func=cmd_list_pending)

    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.set_defaults(func=cmd_init)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
