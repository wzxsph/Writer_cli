"""设定考据 Subagent"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from core.config import get_project_root, load_config


class LoreVerifierSubagent:
    """
    设定考据 Subagent

    职责：
    - 校验世界观规则是否被破坏
    - 校验角色能力是否越界
    - 校验组织结构是否冲突
    - 校验地理、时间、境界、物价是否自洽
    - 校验新增设定是否污染主设定

    上下文隔离原则：最小必要上下文
    """

    def __init__(self):
        self.root = get_project_root()
        self.worldbuild_file = self.root / "WORLDBUILD.md"
        self.characters_file = self.root / "CHARACTERS.md"
        self.timeline_file = self.root / "TIMELINE.md"
        self.powersystem_file = self.root / "POWERSYSTEM.md"

    def load_worldbuild(self) -> str:
        """加载世界观设定"""
        if self.worldbuild_file.exists():
            with open(self.worldbuild_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def load_characters(self) -> str:
        """加载角色设定"""
        if self.characters_file.exists():
            with open(self.characters_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def verify_geography(self, text: str, lore_text: str) -> List[Dict[str, Any]]:
        """校验地理设定一致性"""
        violations = []

        # 提取正文中的地名
        location_pattern = r"([A-Z一-龥]+(?:省|州|城|镇|山|河|海|岛|洲))"
        locations = re.findall(location_pattern, text)

        # 简化的校验：检查地名是否在设定中定义
        # 实际应该更复杂
        if "设定" in lore_text and locations:
            # 占位逻辑
            pass

        return violations

    def verify_timeline(self, text: str, timeline_text: str) -> List[Dict[str, Any]]:
        """校验时间线一致性"""
        violations = []

        # 提取时间表达
        time_patterns = [
            r"(昨日|今日|明日|前几日|后几日)",
            r"(\d+日前|\d+日后|\d+年前|\d+年后)",
            r"(辰时|午时|申时|亥时|夜里|白天)"
        ]

        time_refs = []
        for pattern in time_patterns:
            time_refs.extend(re.findall(pattern, text))

        # 与 TIMELINE.md 比对
        # 简化实现
        return violations

    def verify_power_levels(self, text: str, powersystem_text: str) -> List[Dict[str, Any]]:
        """校验战力等级一致性"""
        violations = []

        # 与 POWERSYSTEM.md 比对
        # 简化实现
        return violations

    def verify_organization_structure(self, text: str, lore_text: str) -> List[Dict[str, Any]]:
        """校验组织结构一致性"""
        violations = []

        # 简化的校验逻辑
        return violations

    def verify(
        self,
        chapter_text: str,
        lore_references: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        执行完整的设定校验

        参数：
        - chapter_text: 需要校验的文本片段（非全文）
        - lore_references: 相关世界观文件的直接引用路径

        返回：校验结果
        {
            "passed": bool,
            "violations": [...],
            "suggestions": [...]
        }
        """
        violations = []
        suggestions = []

        # 读取相关设定文件
        lore_text = self.load_worldbuild()
        characters_text = self.load_characters()
        timeline_text = self.load_timeline() if hasattr(self, 'load_timeline') else ""

        # 校验地理
        geo_violations = self.verify_geography(chapter_text, lore_text)
        violations.extend(geo_violations)

        # 校验时间线
        time_violations = self.verify_timeline(chapter_text, timeline_text)
        violations.extend(time_violations)

        # 校验战力
        power_violations = self.verify_power_levels(chapter_text, self.load_powersystem())
        violations.extend(power_violations)

        # 校验组织结构
        org_violations = self.verify_organization_structure(chapter_text, lore_text)
        violations.extend(org_violations)

        has_blocking = any(v.get("severity") == "blocking" for v in violations)

        return {
            "passed": not has_blocking,
            "violations": violations,
            "suggestions": suggestions
        }

    def load_powersystem(self) -> str:
        """加载战力体系"""
        if self.powersystem_file.exists():
            with open(self.powersystem_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""


class LoreVerifierAgent:
    """
    设定考据 Subagent 的 Agent 封装

    支持 Mailbox 通信
    """

    def __init__(self, mailbox=None):
        self.mailbox = mailbox
        self.verifier = LoreVerifierSubagent()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行校验

        payload 格式：
        {
            "chapter_text": "xxx",  # 需要校验的文本片段
            "lore_references": {...}  # 相关设定路径
        }
        """
        chapter_text = payload.get("chapter_text", "")
        lore_references = payload.get("lore_references", {})

        result = self.verifier.verify(chapter_text, lore_references)

        return {
            "verify_passed": result["passed"],
            "violations": result["violations"],
            "suggestions": result["suggestions"]
        }

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理邮箱消息"""
        sender = message.get("sender")
        payload = message.get("payload", {})

        result = self.run(payload)

        return {
            "id": f"resp_{message.get('id', 'unknown')}",
            "sender": "lore_verifier",
            "recipient": sender,
            "task_id": message.get("task_id"),
            "payload": result,
            "status": "completed"
        }


if __name__ == "__main__":
    # 独立的 Subagent 进程入口
    agent = LoreVerifierAgent()
    # 从 stdin 读取消息并处理
    import sys
    msg = json.load(sys.stdin)
    result = agent.process_message(msg)
    print(json.dumps(result, ensure_ascii=False))
