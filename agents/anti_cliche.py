"""反套路审查 Subagent"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from core.config import get_project_root


class AntiClicheSubagent:
    """
    反套路审查 Subagent

    职责：
    - 检测工业化网文中的疲劳模式
    - 识别套路桥段重复
    - 识别反派降智、主角强行装弱等模式

    上下文隔离原则：仅接收情节摘要（200字以内）和套路库路径
    """

    def __init__(self):
        self.root = get_project_root()
        self.cliche_file = self.root / "CLICHE_PATTERNS.md"
        self.patterns = []
        self._load_patterns()

    def _load_patterns(self) -> None:
        """加载陈词滥调库"""
        if not self.cliche_file.exists():
            # 默认模式
            self.patterns = [
                {"pattern": "猛地一愣", "type": "reaction", "severity": "warning"},
                {"pattern": "心中一凛", "type": "reaction", "severity": "warning"},
                {"pattern": "众人哗然", "type": "reaction", "severity": "warning"},
                {"pattern": "倒吸凉气", "type": "reaction", "severity": "warning"},
                {"pattern": "嘴角抽搐", "type": "reaction", "severity": "warning"},
            ]
            return

        with open(self.cliche_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析模式
        # 格式：- 模式: xxx\n  类型: xxx\n  严重度: warning|critical
        pattern_blocks = re.split(r"(?m)^- ", content)

        for block in pattern_blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            pattern_text = lines[0].strip() if lines else ""
            if not pattern_text:
                continue

            pattern_type = "generic"
            severity = "warning"

            for line in lines[1:]:
                if line.startswith("类型:") or line.startswith("type:"):
                    pattern_type = line.split(":", 1)[1].strip()
                elif line.startswith("严重度:") or line.startswith("severity:"):
                    severity = line.split(":", 1)[1].strip()

            if pattern_text:
                self.patterns.append({
                    "pattern": pattern_text,
                    "type": pattern_type,
                    "severity": severity
                })

    def scan_patterns(self, text: str) -> List[Dict[str, Any]]:
        """扫描文本中的套路模式"""
        findings = []

        for p in self.patterns:
            pattern = p["pattern"]
            matches = list(re.finditer(re.escape(pattern), text))
            if matches:
                findings.append({
                    "pattern": pattern,
                    "type": p["type"],
                    "severity": p["severity"],
                    "count": len(matches),
                    "positions": [m.start() for m in matches]
                })

        return findings

    def calculate_risk_score(self, findings: List[Dict[str, Any]]) -> float:
        """
        计算套路化风险评分

        评分算法：综合考虑模式匹配数量和严重度
        """
        if not findings:
            return 0.0

        score = 0.0
        for f in findings:
            count_weight = min(f["count"] * 0.1, 0.5)  # 每匹配一次加0.1，上限0.5
            severity_weight = 1.0 if f["severity"] == "critical" else 0.5
            score += count_weight * severity_weight

        return min(score, 10.0)  # 上限10分

    def review(
        self,
        summary: str,
        full_text: str = None
    ) -> Dict[str, Any]:
        """
        执行反套路审查

        参数：
        - summary: 本章情节摘要（200字以内）
        - full_text: 完整正文（可选）

        返回：审查结果
        """
        # 只扫描摘要
        findings = self.scan_patterns(summary)

        # 如果有完整文本，也扫描（但不作为主要依据）
        if full_text:
            full_findings = self.scan_patterns(full_text)
            # 合并，保留较高严重度
            for ff in full_findings:
                for f in findings:
                    if f["pattern"] == ff["pattern"]:
                        if ff["count"] > f["count"]:
                            f["count"] = ff["count"]

        risk_score = self.calculate_risk_score(findings)

        return {
            "passed": risk_score < 5.0,
            "risk_score": risk_score,
            "findings": findings,
            "recommendation": "需要修改" if risk_score >= 5.0 else "可接受"
        }


class AntiClicheAgent:
    """
    反套路审查 Subagent 的 Agent 封装

    支持 Mailbox 通信
    """

    def __init__(self, mailbox=None):
        self.mailbox = mailbox
        self.reviewer = AntiClicheSubagent()

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行审查

        payload 格式：
        {
            "summary": "xxx",  # 本章情节摘要（200字以内）
            "full_text": "xxx"  # 完整正文（可选）
        }
        """
        summary = payload.get("summary", "")
        full_text = payload.get("full_text")

        result = self.reviewer.review(summary, full_text)

        return {
            "review_passed": result["passed"],
            "risk_score": result["risk_score"],
            "findings": result["findings"],
            "recommendation": result["recommendation"]
        }

    def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """处理邮箱消息"""
        sender = message.get("sender")
        payload = message.get("payload", {})

        result = self.run(payload)

        return {
            "id": f"resp_{message.get('id', 'unknown')}",
            "sender": "anti_cliche",
            "recipient": sender,
            "task_id": message.get("task_id"),
            "payload": result,
            "status": "completed"
        }


if __name__ == "__main__":
    # 独立的 Subagent 进程入口
    agent = AntiClicheAgent()
    import sys
    msg = json.load(sys.stdin)
    result = agent.process_message(msg)
    print(json.dumps(result, ensure_ascii=False))
