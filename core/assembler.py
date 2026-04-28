"""上下文装配器 - Step 1"""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import get_project_root, load_markdown_file


class ContextAssembler:
    """上下文装配器，负责从本地 Markdown 文件树中读取并拼接上下文"""

    def __init__(self):
        self.root = get_project_root()

    def load_file(self, filename: str) -> str:
        """加载单个 Markdown 文件"""
        filepath = self.root / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def load_worldbuild(self) -> str:
        """加载世界观设定"""
        return self.load_file("WORLDBUILD.md")

    def load_outline(self, vol: str = "VOL_1") -> str:
        """加载当前卷大纲"""
        outline_file = f"OUTLINE.md"
        return self.load_file(outline_file)

    def load_recent_summaries(self, n: int = 3) -> str:
        """加载最近 N 章的摘要"""
        buffer = self.load_file("SUMMARY_BUFFER.md")
        # 提取最近 n 章的摘要
        chapters = self._parse_summaries(buffer, n)
        return "\n\n".join(chapters)

    def _parse_summaries(self, buffer: str, n: int) -> List[str]:
        """解析摘要缓冲区，提取最近 n 章"""
        # 简单实现：按 ### VOL_X Chapter Y 分割
        pattern = r"### (VOL_\d+ Chapter \d+)\n- summary: (.+?)(?=\n###|\Z)"
        matches = re.findall(pattern, buffer, re.DOTALL)
        if not matches:
            return []
        # 返回最近 n 个
        return [f"### {m[0]}\n- summary: {m[1].strip()}" for m in matches[-n:]]

    def load_task_chapter(self, vol: str, chapter: int) -> str:
        """加载当前章节任务指令"""
        task_file = f"TASK_{vol}_CHAPTER_{chapter}.md"
        return self.load_file(task_file)

    def load_memory_snapshot(self, vol: str, chapter: int) -> str:
        """加载动态伏笔追踪快照（当前章节相关的 open 伏笔）"""
        memory = self.load_file("MEMORY.md")
        # 过滤出与本章相关的 open 伏笔
        open_foreshadows = self._filter_open_foreshadows(memory, vol, chapter)
        return open_foreshadows

    def _filter_open_foreshadows(self, memory: str, vol: str, chapter: int) -> str:
        """过滤出状态为 open 且与本章相关的伏笔"""
        pattern = r"- id: (FORESHADOW_\d+)\n\s+status: open\n\s+last_chapter: (\d+)"
        matches = re.findall(pattern, memory)
        if not matches:
            return ""

        # 只保留与当前章节相关的伏笔（last_chapter 接近当前章节）
        relevant = [m for m in matches if int(m[1]) >= chapter - 5]
        if not relevant:
            return ""

        # 提取完整的伏笔条目
        result = []
        for fid, _ in relevant:
            pattern = rf"- id: {fid}.*?(?=- id: |\Z)"
            match = re.search(pattern, memory, re.DOTALL)
            if match:
                result.append(match.group(0))
        return "\n".join(result)

    def load_claude_md(self) -> str:
        """加载全局硬规则锁"""
        return self.load_file("CLAUDE.md")

    def assemble_context(
        self,
        vol: str,
        chapter: int,
        chapter_type: str = "normal"
    ) -> str:
        """
        装配完整上下文块

        按照以下顺序拼接：
        1. CLAUDE.md（硬规则锁）
        2. 当前卷大纲
        3. 最近3章摘要
        4. 当前章节任务指令
        5. 动态伏笔快照
        6. 世界观设定
        """
        parts = []

        # 1. 硬规则锁
        claude = self.load_claude_md()
        if claude:
            parts.append(f"## 全局规则（不可违背）\n{claude}")

        # 2. 当前卷大纲
        outline = self.load_outline(vol)
        if outline:
            parts.append(f"## 当前卷大纲\n{outline}")

        # 3. 最近3章摘要
        recent = self.load_recent_summaries(3)
        if recent:
            parts.append(f"## 最近章节摘要\n{recent}")

        # 4. 当前章节任务指令
        task = self.load_task_chapter(vol, chapter)
        if task:
            parts.append(f"## 当前章节任务\n{task}")

        # 5. 动态伏笔快照
        memory = self.load_memory_snapshot(vol, chapter)
        if memory:
            parts.append(f"## 活跃伏笔追踪\n{memory}")

        # 6. 世界观设定（放在最后，作为背景参考）
        worldbuild = self.load_worldbuild()
        if worldbuild:
            parts.append(f"## 世界观设定\n{worldbuild}")

        return "\n\n---\n\n".join(parts)


def assemble_chapter_context(vol: str, chapter: int, chapter_type: str = "normal") -> str:
    """便捷函数：装配章节上下文"""
    assembler = ContextAssembler()
    return assembler.assemble_context(vol, chapter, chapter_type)
