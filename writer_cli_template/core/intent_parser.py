"""任务意图解析器 - Step 2"""
import json
import re
from typing import Dict, Any, List, Optional


INTENT_PARSER_PROMPT = """你是一个任务解析器。请分析以下上下文和章节任务，仅返回一个结构化的 JSON 对象，不要输出任何其他内容。

JSON 格式要求：
{
    "core_plot_nodes": ["核心情节节点1", "核心情节节点2"],
    "entities_to_appear": ["角色A", "地点B", "道具C"],
    "foreshadow_triggered": true或false,
    "foreshadow_new": ["新增伏笔ID列表，如有"],
    "foreshadow_closed": ["已收束伏笔ID列表，如有"]
}

注意：
- 只返回 JSON，不要包含任何解释或正文内容
- entities_to_appear 仅包含本章需要引用的角色/道具/地点
- foreshadow_triggered 为 true 时才需要填写 foreshadow_new 和 foreshadow_closed
"""


class IntentParser:
    """任务意图解析器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def parse(self, context: str, task: str) -> Dict[str, Any]:
        """
        解析任务意图

        返回结构化 JSON：
        - core_plot_nodes: 核心情节节点列表
        - entities_to_appear: 本章需要出现的实体列表
        - foreshadow_triggered: 是否触发伏笔
        - foreshadow_new: 新增伏笔 ID 列表
        - foreshadow_closed: 已收束伏笔 ID 列表
        """
        if self.llm_client is None:
            # 无 LLM 客户端时返回空结果（用于测试）
            return {
                "core_plot_nodes": [],
                "entities_to_appear": [],
                "foreshadow_triggered": False,
                "foreshadow_new": [],
                "foreshadow_closed": []
            }

        prompt = f"{INTENT_PARSER_PROMPT}\n\n## 上下文\n{context}\n\n## 章节任务\n{task}"

        # 获取正确的消息接口（MiniMax: client.messages()，Mock: client.messages）
        messages_interface = self.llm_client.messages
        if callable(messages_interface):
            messages_interface = messages_interface()

        response = messages_interface.create(
            model="minimax-m2.7",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response.content[0].text.strip()

        # 提取 JSON
        try:
            # 尝试从代码块中提取
            json_match = re.search(r"```json\s*(.+?)\s*```", raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = raw_output

            result = json.loads(json_str)
            return result
        except json.JSONDecodeError:
            # 解析失败时返回默认值
            return {
                "core_plot_nodes": [],
                "entities_to_appear": [],
                "foreshadow_triggered": False,
                "foreshadow_new": [],
                "foreshadow_closed": []
            }

    def parse_from_llm_response(self, raw_output: str) -> Dict[str, Any]:
        """从 LLM 原始输出解析 JSON"""
        try:
            json_match = re.search(r"```json\s*(.+?)\s*```", raw_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_output
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {
                "core_plot_nodes": [],
                "entities_to_appear": [],
                "foreshadow_triggered": False,
                "foreshadow_new": [],
                "foreshadow_closed": []
            }
