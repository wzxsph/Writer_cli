"""5级防OOM压缩管线"""
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from core.config import get_project_root


class Compressor:
    """
    5级防OOM压缩管线

    Level 1: 原文截断 - 原始章节文本不进入下一章上下文
    Level 2: 章节级摘要压缩 - 2000字正文压缩为200字摘要
    Level 3: 滚动窗口淘汰 - 维持最近10章摘要，超出进入冷存储
    Level 4: 废稿清洗 - 修正循环中的中间产物不进入主上下文
    Level 5: 定期去重收束 - closed伏笔迁移至冷存储
    """

    def __init__(self):
        self.root = get_project_root()
        self.summary_buffer_file = self.root / "SUMMARY_BUFFER.md"
        self.archive_summary_file = self.root / "ARCHIVE_SUMMARY.md"
        self.memory_file = self.root / "MEMORY.md"
        self.memory_closed_file = self.root / "MEMORY_CLOSED.md"

    def level1_truncate_raw(self, chapter_path: Path) -> str:
        """
        Level 1: 原文截断

        将章节原文归档到 chapters/ 目录，生成路径引用而非内容注入
        """
        if not chapter_path.exists():
            return ""

        return f"[章节原文已归档: {chapter_path.relative_to(self.root)}]"

    def level2_compress_to_summary(
        self,
        chapter_text: str,
        vol: str,
        chapter: int,
        llm_client=None
    ) -> str:
        """
        Level 2: 章节级摘要压缩

        将2000字正文压缩为200字以内的叙事性摘要
        """
        if llm_client is None:
            # 无 LLM 时返回占位符
            return f"{vol} Chapter {chapter}: [摘要待生成]"

        prompt = f"""请将以下章节正文压缩为200字以内的叙事性摘要。

要求：
- 保留：情节锚点、人物状态变更、引发后续的情节钩子
- 舍弃：修辞性描写、细节场景

## 正文
{chapter_text[:5000]}  # 限制输入长度

## 输出格式
仅输出摘要文本，不要包含任何解释"""

        messages_interface = llm_client.messages
        if callable(messages_interface):
            messages_interface = messages_interface()
        response = messages_interface.create(
            model="minimax-m2.7",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        summary = response.content[0].text.strip()
        return summary

    def level3_rolling_window(
        self,
        new_summary: str,
        vol: str,
        chapter: int,
        max_buffer: int = 10
    ) -> None:
        """
        Level 3: 滚动窗口淘汰

        维持最近 N 章摘要，超出部分写入冷存储
        """
        # 读取当前缓冲区
        buffer_content = ""
        if self.summary_buffer_file.exists():
            with open(self.summary_buffer_file, "r", encoding="utf-8") as f:
                buffer_content = f.read()

        # 解析现有摘要
        existing = self._parse_summaries(buffer_content)

        # 添加新摘要
        new_entry = {
            "vol": vol,
            "chapter": chapter,
            "summary": new_summary
        }
        existing.append(new_entry)

        # 检查是否超出窗口
        overflow = []
        if len(existing) > max_buffer:
            overflow = existing[:len(existing) - max_buffer]
            existing = existing[len(existing) - max_buffer:]

        # 写回缓冲区
        self._write_summary_buffer(existing)

        # 溢出部分写入冷存储
        if overflow:
            self._append_to_archive(overflow)

    def _parse_summaries(self, content: str) -> List[Dict[str, Any]]:
        """解析摘要缓冲区"""
        pattern = r"### (VOL_\d+ Chapter \d+)\n- summary: (.+?)(?=\n###|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)
        result = []
        for vol_ch, summary in matches:
            parts = vol_ch.split()
            result.append({
                "vol": parts[0],
                "chapter": int(parts[2]),
                "summary": summary.strip()
            })
        return result

    def _write_summary_buffer(self, summaries: List[Dict[str, Any]]) -> None:
        """写回摘要缓冲区"""
        lines = ["# 滚动摘要缓冲区", "", "## 最近 N 章摘要", ""]

        for s in summaries:
            lines.append(f"### {s['vol']} Chapter {s['chapter']}")
            lines.append(f"- summary: {s['summary']}")
            lines.append(f"- char_states: [{', '.join(s.get('char_states', []))}]")
            lines.append(f"- foreshadow_new: [{', '.join(s.get('foreshadow_new', []))}]")
            lines.append(f"- foreshadow_closed: [{', '.join(s.get('foreshadow_closed', []))}]")
            lines.append("")

        with open(self.summary_buffer_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _append_to_archive(self, overflow: List[Dict[str, Any]]) -> None:
        """追加溢出摘要到冷存储"""
        lines = []
        for s in overflow:
            lines.append(f"### {s['vol']} Chapter {s['chapter']}")
            lines.append(f"- summary: {s['summary']}")
            lines.append("")

        with open(self.archive_summary_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def level4_discard_draft_context(self) -> None:
        """
        Level 4: 废稿上下文清洗

        此级由调用方在修正循环完成后丢弃临时上下文
        本方法仅作为文档说明，不执行实际清理
        """
        # 修正 Prompt 及模型的修正响应在局部修正循环中形成独立 turn-pair
        # 修正完成并校验通过后，临时上下文被丢弃
        pass

    def level5_dedup_memory(self, arc_boundary: bool = False) -> None:
        """
        Level 5: MEMORY.md 定期去重收束

        1. 将状态为 closed 的伏笔条目迁移至 MEMORY_CLOSED.md
        2. 对状态为 dormant（超过N章未被引用）的条目执行强制关闭
        """
        if not self.memory_file.exists():
            return

        with open(self.memory_file, "r", encoding="utf-8") as f:
            memory_content = f.read()

        # 解析伏笔条目
        pattern = r"- id: (FORESHADOW_\d+)\n\s+status: (\w+)\n\s+last_chapter: (\d+)"
        matches = re.findall(pattern, memory_content)

        open_entries = []
        closed_entries = []
        dormant_entries = []

        current_chapter = self._get_current_chapter()

        for fid, status, last_ch in matches:
            entry_pattern = rf"- id: {fid}\n\s+status: {status}\n\s+last_chapter: {last_ch}.*?(?=- id: |\Z)"
            entry_match = re.search(entry_pattern, memory_content, re.DOTALL)

            if status == "closed":
                closed_entries.append(entry_match.group(0) if entry_match else f"- id: {fid}")
            elif status == "open" and current_chapter - int(last_ch) > 5:
                # 超过5章未被引用，标记为 dormant
                dormant_entries.append(entry_match.group(0) if entry_match else f"- id: {fid}")
            else:
                open_entries.append(entry_match.group(0) if entry_match else f"- id: {fid}")

        # 写回 MEMORY.md（仅保留 open 和 dormant）
        self._write_memory(open_entries + dormant_entries)

        # 追加 closed 到冷存储
        if closed_entries:
            with open(self.memory_closed_file, "a", encoding="utf-8") as f:
                f.write("\n".join(closed_entries) + "\n")

    def _get_current_chapter(self) -> int:
        """获取当前章节号"""
        schedule_file = self.root / "SCHEDULE.md"
        if schedule_file.exists():
            with open(schedule_file, "r", encoding="utf-8") as f:
                content = f.read()
            match = re.search(r"chapter:\s*(\d+)", content)
            if match:
                return int(match.group(1))
        return 0

    def _write_memory(self, entries: List[str]) -> None:
        """写回 MEMORY.md"""
        lines = ["# 动态伏笔状态机", "", "## 伏笔条目格式", "# - id: FORESHADOW_001", "#   status: open|closed|dormant", "#   last_chapter: 1", "#   keywords: [关键词1, 关键词2]", "", "## 角色状态变更", "# - char: 角色名", "#   change: 状态变更描述", "#   chapter: 章节号", ""]

        if entries:
            lines.append("## 伏笔条目")
            lines.append("")
            lines.extend(entries)

        with open(self.memory_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


def get_compressor() -> Compressor:
    """获取压缩器实例"""
    return Compressor()
