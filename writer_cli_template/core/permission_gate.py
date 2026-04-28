"""权限门控预检器 - Step 3"""
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from core.config import get_project_root


class PermissionGate:
    """
    权限门控预检器

    在正文生成前执行硬性拦截，检查高危操作：
    - 核心角色死亡（名单锁定在 PROTECTED_CHARS.md）
    - 世界观底层设定更改
    - 已公开伏笔的强制关闭
    """

    def __init__(self):
        self.root = get_project_root()

    def load_file(self, filename: str) -> str:
        """加载文件内容"""
        filepath = self.root / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def check_protected_chars(self, text: str, intent: Dict[str, Any]) -> List[str]:
        """
        检查是否涉及核心角色死亡

        返回：违规列表
        """
        violations = []
        protected = self.load_file("PROTECTED_CHARS.md")

        # 提取受保护角色名单
        pattern = r"## 不可死亡角色\s*\n(.+?)(?:\n##|\Z)"
        match = re.search(pattern, protected, re.DOTALL)
        if not match:
            return violations

        lines = match.group(1).strip().split("\n")
        protected_chars = [l.strip().lstrip("- ").strip() for l in lines if l.strip()]

        # 检查文本中是否出现"XX死亡"、"XX被杀"等表达
        death_patterns = [
            r"{char}(?:死了|死亡|被杀|被灭|陨落|身亡)",
            r"(?:杀了|杀死|灭掉){char}",
        ]

        for char in protected_chars:
            if not char or char.startswith("["):
                continue
            for pattern in death_patterns:
                if re.search(pattern.format(char=char), text):
                    violations.append(f"核心角色 {char} 涉及死亡情节（受保护角色）")

        return violations

    def check_worldbuild_alteration(self, text: str) -> List[str]:
        """
        检查是否试图修改世界观底层设定

        返回：违规列表
        """
        violations = []
        worldbuild = self.load_file("WORLDBUILD.md")

        # 提取世界观核心规则（物理规则部分）
        pattern = r"## 物理规则\s*\n(.+?)(?:\n##|\Z)"
        match = re.search(pattern, worldbuild, re.DOTALL)
        if not match:
            return violations

        # 简化的检查：如果文本中提到修改/废除/颠覆物理规则
        alteration_keywords = ["修改", "废除", "颠覆", "改变物理", "规则失效"]
        for keyword in alteration_keywords:
            if keyword in text:
                violations.append(f"检测到可能修改世界观底层设定的内容：{keyword}")

        return violations

    def check_foreshadow_violations(self, intent: Dict[str, Any], text: str) -> List[str]:
        """
        检查伏笔相关违规

        - 不能删除未收束的伏笔
        - 伏笔关闭必须有前文依据
        """
        violations = []

        if not intent.get("foreshadow_triggered"):
            return violations

        closed_ids = intent.get("foreshadow_closed", [])
        if not closed_ids:
            return violations

        memory = self.load_file("MEMORY.md")

        for fid in closed_ids:
            # 检查该伏笔是否存在于 MEMORY.md 中
            if f"- id: {fid}" not in memory:
                continue

            # 检查伏笔状态是否为 open
            pattern = rf"- id: {fid}\n\s+status: (\w+)"
            match = re.search(pattern, memory)
            if match and match.group(1) != "open":
                violations.append(f"伏笔 {fid} 状态并非 open，无法收束")

        return violations

    def pre_check(self, text: str, intent: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        执行权限门控预检

        返回：(是否通过, 违规列表)
        """
        all_violations = []

        # 检查 1：核心角色死亡
        char_violations = self.check_protected_chars(text, intent)
        all_violations.extend(char_violations)

        # 检查 2：世界观修改
        worldbuild_violations = self.check_worldbuild_alteration(text)
        all_violations.extend(worldbuild_violations)

        # 检查 3：伏笔违规
        foreshadow_violations = self.check_foreshadow_violations(intent, text)
        all_violations.extend(foreshadow_violations)

        passed = len(all_violations) == 0
        return passed, all_violations


def check_permission(text: str, intent: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """便捷函数：执行权限检查"""
    gate = PermissionGate()
    return gate.pre_check(text, intent)
