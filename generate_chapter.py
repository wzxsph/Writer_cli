#!/usr/bin/env python3
"""
单章生成工作流

功能：
1. 生成指定章节
2. 生成后更新 MEMORY.md
3. 生成下一章 TASK 文件
4. 更新 SCHEDULE.md

用法：
    python generate_chapter.py --vol VOL_1 --chapter 2
"""

import argparse
import os
import re
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config import get_project_root, load_config
from core.generator import create_llm_client, get_generator
from core.assembler import assemble_chapter_context
from core.intent_parser import IntentParser
from core.scheduler import get_scheduler
from sandbox.validator import SandboxValidator


def load_env():
    """加载环境变量"""
    env_file = Path(__file__).parent.parent / "env"
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    key, value = line[7:].split("=", 1)
                    os.environ[key.strip()] = value.strip()


def generate_chapter(vol: str, chapter: int, chapter_type: str = None) -> tuple:
    """
    生成单个章节

    返回：(成功标志, 消息, 字数)
    """
    print(f"\n{'='*60}")
    print(f"开始生成 {vol} Chapter {chapter}")
    print(f"{'='*60}\n")

    # 1. 加载配置和客户端
    load_env()
    config = load_config()
    llm_client = create_llm_client()
    generator = get_generator(llm_client)
    intent_parser = IntentParser(llm_client)
    validator = SandboxValidator()
    scheduler = get_scheduler()

    # 2. 确定章节类型
    if chapter_type is None:
        # 从 TASK 文件读取
        task_file = get_project_root() / f"TASK_{vol}_CHAPTER_{chapter}.md"
        if task_file.exists():
            with open(task_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "## 任务类型" in content:
                match = re.search(r"## 任务类型\s*\n(\w+)", content)
                if match:
                    chapter_type = match.group(1)
        if chapter_type is None:
            chapter_type = "normal"

    # 3. 上下文装配
    print("[1/6] 上下文装配...")
    context = assemble_chapter_context(vol, chapter, chapter_type)
    if not context:
        return False, "上下文装配失败", 0

    # 4. 意图解析
    print("[2/6] 意图解析...")
    task_file = get_project_root() / f"TASK_{vol}_CHAPTER_{chapter}.md"
    task_content = ""
    if task_file.exists():
        with open(task_file, "r", encoding="utf-8") as f:
            task_content = f.read()

    intent = intent_parser.parse(context, task_content)

    # 5. 正文生成
    print("[3/6] 正文生成...")
    word_config = config.chapter_word_count.get(
        chapter_type,
        config.chapter_word_count["normal"]
    )

    text = generator.generate_chapter(
        context=context,
        task=task_content,
        vol=vol,
        chapter=chapter,
        chapter_type=chapter_type
    )

    if not text:
        return False, "正文生成失败", 0

    char_count = len(text)
    print(f"      生成字数: {char_count}")

    # 6. 沙盒校验
    print("[4/6] 沙盒校验...")
    validation = validator.validate_all(
        text=text,
        vol=vol,
        chapter=chapter,
        chapter_type=chapter_type,
        min_word_count=word_config.min,
        max_word_count=word_config.max,
        llm_client=llm_client
    )

    if not validation["passed"]:
        violations = validation.get("violations", [])
        blocking = [v for v in violations if v.get("severity") == "blocking"]
        if blocking:
            reasons = [v.get("reason", "未知") for v in blocking]
            return False, f"校验失败: {'; '.join(reasons)}", char_count

    # 7. 章节归档
    print("[5/6] 章节归档...")
    chapters_dir = get_project_root() / "chapters" / vol
    chapters_dir.mkdir(parents=True, exist_ok=True)
    chapter_file = chapters_dir / f"CHAPTER_{chapter}.md"

    # 原子性写入
    tmp_file = chapter_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        f.write(text)
    tmp_file.rename(chapter_file)

    # 8. 更新调度器
    print("[6/6] 更新状态...")
    next_chapter = chapter + 1
    next_vol = vol

    # 生成下一章 TASK 文件
    next_task_file = get_project_root() / f"TASK_{next_vol}_CHAPTER_{next_chapter}.md"
    if not next_task_file.exists():
        # 从 OUTLINE.md 提取下一章信息
        outline_file = get_project_root() / "OUTLINE.md"
        if outline_file.exists():
            with open(outline_file, "r", encoding="utf-8") as f:
                outline = f.read()

            # 查找下一章锚点
            pattern = rf"### {next_vol} Chapter {next_chapter}\s*\n- anchor: (.+?)\n- foreshadow_ids: \[(.*?)\]\n- pov: (.+?)\n- type: (.+)"
            match = re.search(pattern, outline, re.DOTALL)

            if match:
                anchor = match.group(1).strip()
                foreshadow_ids = match.group(2).strip()
                pov = match.group(3).strip()
                ch_type = match.group(4).strip()

                next_task_content = f"""# {next_vol} Chapter {next_chapter} 任务

## 任务类型
{ch_type}

## 章节锚点
{anchor}

## 应激活的伏笔
[{foreshadow_ids}]

## 叙事视角
{pov}

## 字数要求
{ch_type}

## 章节目标
[待填写]

## 写作风格要求
- 对话用「」标记
- 环境描写用具体细节
- 心理活动通过动作展现
- 章节结尾留钩子
"""
                with open(next_task_file, "w", encoding="utf-8") as f:
                    f.write(next_task_content)

    # 推进调度器
    scheduler.mark_done(vol, chapter)
    scheduler.save_schedule({
        "current_task": {
            "volume": next_vol,
            "chapter": next_chapter,
            "status": "READY",
            "created_at": datetime.now().isoformat()
        }
    })

    print(f"\n{'='*60}")
    print(f"✓ {vol} Chapter {chapter} 生成完成")
    print(f"  字数: {char_count}")
    print(f"  下一章: {next_vol} Chapter {next_chapter}")
    print(f"{'='*60}\n")

    return True, f"完成", char_count


def main():
    parser = argparse.ArgumentParser(description="单章生成工作流")
    parser.add_argument("--vol", required=True, help="卷名，如 VOL_1")
    parser.add_argument("--chapter", type=int, required=True, help="章节号")
    parser.add_argument("--type", choices=["normal", "climax", "transition"],
                        help="章节类型")

    args = parser.parse_args()

    success, message, char_count = generate_chapter(args.vol, args.chapter, args.type)

    if success:
        print(f"成功: {message}")
        sys.exit(0)
    else:
        print(f"失败: {message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
