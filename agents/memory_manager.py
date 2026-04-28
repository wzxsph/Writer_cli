"""伏笔管理 Subagent"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.config import get_project_root


class MemoryManagerSubagent:
    """
    伏笔管理 Subagent

    职责：
    - 识别新增伏笔
    - 标记伏笔推进
    - 标记伏笔回收
    - 检查长期悬置伏笔
    - 防止模型遗忘早期承诺

    上下文隔离原则：仅接收正文片段，不接收完整上下文
    """

    def __init__(self):
        self.root = get_project_root()
        self.memory_file = self.root / "MEMORY.md"

    def load_memory(self) -> str:
        """加载当前记忆"""
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def parse_memory_entries(self, memory_text: str) -> List[Dict[str, Any]]:
        """解析伏笔条目"""
        entries = []

        # 格式：
        # - id: FORESHADOW_001
        #   status: open
        #   last_chapter: 1
        #   keywords: [关键词1, 关键词2]
        pattern = r"- id: (FORESHADOW_\d+)\n\s+status: (open|closed|dormant)\n\s+last_chapter: (\d+)(?:\n\s+keywords: \[(.+?)\])?"

        for match in re.finditer(pattern, memory_text):
            entries.append({
                "id": match.group(1),
                "status": match.group(2),
                "last_chapter": int(match.group(3)),
                "keywords": [k.strip() for k in match.group(4).split(",")] if match.group(4) else []
            })

        return entries

    def identify_new_foreshadows(
        self,
        text: str,
        current_chapter: int,
        existing_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        识别正文中的新增伏笔

        返回：[{id, keywords}, ...]
        """
        new_foreshadows = []

        # 简化的伏笔识别：
        # 1. 查找"为后续...埋下伏笔"等表达
        # 2. 查找悬念性描述

        hint_patterns = [
            r"为后续(.+?)埋下伏笔",
            r"这件事(.+?)绝不简单",
            r"(.+?)的秘密",
            r"未来某天(.+?)将会"
        ]

        foreshadow_texts = []
        for pattern in hint_patterns:
            matches = re.findall(pattern, text)
            foreshadow_texts.extend(matches)

        # 生成新伏笔 ID
        max_id = 0
        for eid in existing_ids:
            match = re.search(r"FORESHADOW_(\d+)", eid)
            if match:
                max_id = max(max_id, int(match.group(1)))

        for i, fs_text in enumerate(foreshadow_texts[:3]):  # 最多3个新伏笔
            new_id = f"FORESHADOW_{max_id + i + 1:03d}"
            keywords = self._extract_keywords(fs_text)
            new_foreshadows.append({
                "id": new_id,
                "keywords": keywords,
                "trigger_text": fs_text
            })

        return new_foreshadows

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简化的关键词提取
        # 实际应该用 NLP
        keywords = []
        for word in text.split()[:3]:
            if len(word) >= 2:
                keywords.append(word)
        return keywords

    def identify_closed_foreshadows(
        self,
        text: str,
        open_entries: List[Dict[str, Any]]
    ) -> List[str]:
        """
        识别被收束的伏笔

        返回：已收束的伏笔 ID 列表
        """
        closed = []

        for entry in open_entries:
            keywords = entry.get("keywords", [])
            for kw in keywords:
                if kw in text:
                    # 检查是否有收束性表达
                    close_patterns = ["终于", "原来", "竟然", "揭晓", "真相大白"]
                    if any(p in text for p in close_patterns):
                        closed.append(entry["id"])
                        break

        return closed

    def update_memory(
        self,
        new_foreshadows: List[Dict[str, Any]],
        closed_ids: List[str],
        current_chapter: int
    ) -> Dict[str, Any]:
        """
        更新 MEMORY.md

        返回：更新建议
        """
        memory_text = self.load_memory()
        entries = self.parse_memory_entries(memory_text)

        # 标记已收束的伏笔
        for entry in entries:
            if entry["id"] in closed_ids:
                entry["status"] = "closed"

        # 添加新伏笔
        for fs in new_foreshadows:
            entries.append({
                "id": fs["id"],
                "status": "open",
                "last_chapter": current_chapter,
                "keywords": fs.get("keywords", [])
            })

        # 生成更新后的 MEMORY.md 内容
        lines = ["# 动态伏笔状态机", "", "## 伏笔条目格式", "# - id: FORESHADOW_001", "#   status: open|closed|dormant", "#   last_chapter: 1", "#   keywords: [关键词1, 关键词2]", "", "## 伏笔条目", ""]

        for entry in entries:
            lines.append(f"- id: {entry['id']}")
            lines.append(f"  status: {entry['status']}")
            lines.append(f"  last_chapter: {entry['last_chapter']}")
            lines.append(f"  keywords: [{', '.join(entry.get('keywords', []))}]")
            lines.append("")

        # 角色状态变更部分（追加）
        lines.append("## 角色状态变更")
        lines.append("# - char: 角色名")
        lines.append("#   change: 状态变更描述")
        lines.append("#   chapter: 章节号")

        return {
            "new_memory_content": "\n".join(lines),
            "new_foreshadows": new_foreshadows,
            "closed_ids": closed_ids
        }

    def analyze(
        self,
        text: str,
        current_chapter: int
    ) -> Dict[str, Any]:
        """
        分析正文并生成记忆更新建议

        返回：分析结果
        """
        memory_text = self.load_memory()
        entries = self.parse_memory_entries(memory_text)
        open_entries = [e for e in entries if e["status"] == "open"]
        existing_ids = [e["id"] for e in entries]

        # 识别新伏笔
        new_foreshadows = self.identify_new_foreshadows(text, current_chapter, existing_ids)

        # 识别已收束伏笔
        closed_ids = self.identify_closed_foreshadows(text, open_entries)

        # 生成更新建议
        update_suggestion = self.update_memory(new_foreshadows, closed_ids, current_chapter)

        return {
            "new_foreshadows": new_foreshadows,
            "closed_ids": closed_ids,
            "update_suggestion": update_suggestion
        }


class MemoryManagerAgent:
    """
    伏笔管理 Subagent 的 Agent 封装

    支持 Mailbox 通信
    """

    def __init__(self, mailbox=None):
        self.mailbox = mailbox
        self.manager = MemoryManagerSubagent()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行伏笔管理

        payload 格式：
        {
            "text": "xxx",  # 本章正文片段
            "current_chapter": 1
        }
        """
        text = payload.get("text", "")
        current_chapter = payload.get("current_chapter", 1)

        result = self.manager.analyze(text, current_chapter)

        return {
            "new_foreshadows": result["new_foreshadows"],
            "closed_ids": result["closed_ids"],
            "update_suggestion": result["update_suggestion"]
        }

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理邮箱消息"""
        sender = message.get("sender")
        payload = message.get("payload", {})

        result = self.run(payload)

        return {
            "id": f"resp_{message.get('id', 'unknown')}",
            "sender": "memory_manager",
            "recipient": sender,
            "task_id": message.get("task_id"),
            "payload": result,
            "status": "completed"
        }


if __name__ == "__main__":
    agent = MemoryManagerAgent()
    import sys
    msg = json.load(sys.stdin)
    result = agent.process_message(msg)
    print(json.dumps(result, ensure_ascii=False))
