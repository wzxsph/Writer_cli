"""调度器 - Step 9"""
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from core.config import get_project_root


class Scheduler:
    """
    任务调度器

    负责：
    - 读取 SCHEDULE.md 中的任务队列
    - 更新任务状态（PENDING → READY → IN_PROGRESS → DONE）
    - 生成下一章的 TASK 文件
    - 推进大纲游标
    """

    def __init__(self):
        self.root = get_project_root()
        self.schedule_file = self.root / "SCHEDULE.md"

    def load_schedule(self) -> Dict[str, Any]:
        """加载调度队列"""
        if not self.schedule_file.exists():
            return {"current_task": None, "queue": []}

        with open(self.schedule_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单解析：提取当前任务和队列信息
        # 实际实现应该用更好的格式/存储
        result = {"current_task": None, "queue": []}

        # 解析当前任务
        current_match = re.search(
            r"## 当前任务\s*\n.*?volume:\s*(\w+)\s*\n.*?chapter:\s*(\d+)\s*\n.*?status:\s*(\w+)",
            content,
            re.DOTALL
        )
        if current_match:
            result["current_task"] = {
                "volume": current_match.group(1),
                "chapter": int(current_match.group(2)),
                "status": current_match.group(3)
            }

        return result

    def save_schedule(self, schedule: Dict[str, Any]) -> None:
        """保存调度队列"""
        lines = ["# 任务调度队列", "", "## 队列状态", "", "- PENDING: 等待中", "- READY: 可执行", "- IN_PROGRESS: 执行中", "- DONE: 已完成", "- FAILED: 失败", ""]

        if schedule.get("current_task"):
            task = schedule["current_task"]
            lines.append("## 当前任务")
            lines.append("")
            lines.append(f"- volume: {task.get('volume', 'VOL_1')}")
            lines.append(f"- chapter: {task.get('chapter', 1)}")
            lines.append(f"- status: {task.get('status', 'READY')}")
            lines.append(f"- created_at: {task.get('created_at', datetime.now().isoformat())}")

        with open(self.schedule_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个待执行任务"""
        schedule = self.load_schedule()
        current = schedule.get("current_task")

        if current and current.get("status") == "READY":
            return current

        return None

    def mark_in_progress(self, vol: str, chapter: int) -> None:
        """标记任务为执行中"""
        schedule = self.load_schedule()
        if schedule.get("current_task"):
            schedule["current_task"]["status"] = "IN_PROGRESS"
        else:
            schedule["current_task"] = {
                "volume": vol,
                "chapter": chapter,
                "status": "IN_PROGRESS",
                "created_at": datetime.now().isoformat()
            }
        self.save_schedule(schedule)

    def mark_done(self, vol: str, chapter: int) -> None:
        """标记任务为已完成"""
        schedule = self.load_schedule()
        if schedule.get("current_task"):
            schedule["current_task"]["status"] = "DONE"
        self.save_schedule(schedule)

    def mark_failed(self, vol: str, chapter: int, reason: str) -> None:
        """标记任务为失败"""
        schedule = self.load_schedule()
        if schedule.get("current_task"):
            schedule["current_task"]["status"] = "FAILED"
            schedule["current_task"]["failed_reason"] = reason
        self.save_schedule(schedule)

    def advance_to_next(self, vol: str, current_chapter: int) -> Dict[str, Any]:
        """
        推进到下一章

        1. 将当前章节标记为 DONE
        2. 生成下一章的 TASK 文件
        3. 更新调度队列
        """
        # 标记当前完成
        self.mark_done(vol, current_chapter)

        next_chapter = current_chapter + 1

        # 生成下一章 TASK 文件
        self._generate_task_file(vol, next_chapter)

        # 更新调度队列
        schedule = self.load_schedule()
        schedule["current_task"] = {
            "volume": vol,
            "chapter": next_chapter,
            "status": "READY",
            "created_at": datetime.now().isoformat()
        }
        self.save_schedule(schedule)

        return {
            "volume": vol,
            "chapter": next_chapter,
            "status": "READY"
        }

    def _generate_task_file(self, vol: str, chapter: int) -> None:
        """生成章节任务文件"""
        task_file = self.root / f"TASK_{vol}_CHAPTER_{chapter}.md"

        # 从 OUTLINE.md 读取本章的大纲锚点
        outline_file = self.root / "OUTLINE.md"
        anchor = ""
        foreshadow_ids = []

        if outline_file.exists():
            with open(outline_file, "r", encoding="utf-8") as f:
                outline = f.read()

            # 提取本章锚点
            pattern = rf"### {vol} Chapter {chapter}\s*\n.*?anchor:\s*(.+?)(?:\n\s*foreshadow|$)"
            match = re.search(pattern, outline, re.DOTALL)
            if match:
                anchor = match.group(1).strip()

            # 提取伏笔 ID
            pattern = rf"### {vol} Chapter {chapter}\s*\n.*?foreshadow_ids:\s*\[(.+?)\]"
            match = re.search(pattern, outline, re.DOTALL)
            if match:
                ids_str = match.group(1)
                foreshadow_ids = [x.strip() for x in ids_str.split(",") if x.strip()]

        # 从 chapter_titles.txt 读取章节标题
        chapter_title = self._get_chapter_title(vol, chapter)

        # 生成 TASK 文件
        lines = [
            f"# {vol} Chapter {chapter} 任务",
            "",
            "## 章节标题",
            chapter_title,
            "",
            "## 任务类型",
            "normal",
            "",
            "## 章节锚点",
            anchor or "[待填写本章核心情节锚点]",
            "",
            "## 应激活的伏笔",
            f"[{', '.join(foreshadow_ids) if foreshadow_ids else '无'}]",
            "",
            "## 叙事视角",
            "第三人称",
            "",
            "## 字数要求",
            "normal",
        ]

        with open(task_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _get_chapter_title(self, vol: str, chapter: int) -> str:
        """从 chapter_titles.txt 读取章节标题"""
        titles_file = self.root / "chapter_titles.txt"
        if not titles_file.exists():
            return "[待填写章节标题]"

        with open(titles_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 匹配格式: Ch01: 第1章 标题
        pattern = rf"Ch{chapter:02d}:\s*第{chapter}章\s+(.+)"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()

        # 备选匹配: 第X章 标题
        pattern = rf"第{chapter}章\s+(.+)"
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()

        return "[待填写章节标题]"


def get_scheduler() -> Scheduler:
    """获取调度器实例"""
    return Scheduler()
