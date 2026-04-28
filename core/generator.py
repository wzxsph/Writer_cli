"""正文生成器 - Step 4"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any
from core.config import load_config, get_project_root


CHAPTER_WRITING_PROMPT_TEMPLATE = """你是一个专业的网文写手。请根据以下上下文和任务要求，生成章节正文。

## 写作要求
- 输出格式：纯叙事散文
- 禁止包含章节元数据或 Markdown 标记
- 禁止输出任何解释性文字
- 字数区间：{word_count_min}-{word_count_max} 字
- 叙事视角：{pov}
- 对话必须用「」标记，如：「你好」「谢谢」
- 开头直接切入场景，不要铺垫
- 环境描写用具体细节展现（声音、气味、温度、光线）
- 心理活动通过动作和对话展现，不直接描写内心
- 章节结尾必须留钩子，引发读者继续阅读
- 节奏：事件驱动，层层递进

## 上下文
{context}

## 章节任务
{task}

请开始写作："""


class ContentGenerator:
    """正文生成器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.config = load_config()

    def generate_chapter(
        self,
        context: str,
        task: str,
        vol: str,
        chapter: int,
        chapter_type: str = "normal",
        pov: str = "第三人称"
    ) -> Optional[str]:
        """
        生成章节正文

        参数：
        - context: 装配好的上下文
        - task: 当前章节任务
        - vol: 当前卷
        - chapter: 当前章节号
        - chapter_type: 章节类型（normal/climax/transition）
        - pov: 叙事视角

        返回：生成的正文，或 None（生成失败）
        """
        if self.llm_client is None:
            print("[Generator] 警告：无 LLM 客户端，返回 None")
            return None

        # 获取字数配置
        word_config = self.config.chapter_word_count.get(
            chapter_type,
            self.config.chapter_word_count["normal"]
        )

        # 构建 Prompt
        prompt = CHAPTER_WRITING_PROMPT_TEMPLATE.format(
            word_count_min=word_config.min,
            word_count_max=word_config.max,
            pov=pov,
            context=context,
            task=task
        )

        # 调用 LLM
        messages_interface = self.llm_client.messages
        if callable(messages_interface):
            messages_interface = messages_interface()
        response = messages_interface.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response.content[0].text.strip()

        # 后处理：去除可能的 Markdown 标记和解释性文字
        cleaned = self._clean_output(raw_output)

        return cleaned

    def _clean_output(self, text: str) -> str:
        """
        清理输出：
        - 去除 Markdown 标记
        - 去除可能的"以下是"、"作为AI"等非正文内容
        - 去除章节标题格式
        """
        import re

        # 去除代码块标记
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        # 去除"作为 AI"、"以下是"等开头
        text = re.sub(r"^(作为 AI|以下是|根据您的要求|根据上下文).*?\n", "", text)

        # 去除章节标题标记（# 第一章 标题 等）
        text = re.sub(r"^#+\s*第[一二三四五六七八九十百\d]+章.*?\n", "", text)

        # 去除"第X章"的独立行
        text = re.sub(r"^第[一二三四五六七八九十百\d]+章\s*$", "", text, flags=re.MULTILINE)

        # 去除多余的空行（保留最多两个连续空行）
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()


class MockLLMClient:
    """模拟 LLM 客户端（用于测试）"""

    def __init__(self):
        self.messages = MockMessages()


class MockMessages:
    """模拟 LLM 消息接口"""

    def create(self, **kwargs):
        class MockResponse:
            content = [type('obj', (object,), {'text': '这是模拟生成的章节正文内容...'})()]
        return MockResponse()


class MiniMaxLLMClient:
    """
    MiniMax API 客户端

    支持 MiniMax 的 Anthropic 兼容 API 端点
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.environ.get(
            "ANTHROPIC_BASE_URL",
            "https://api.minimaxi.com/anthropic"
        )
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

    def _make_request(self, payload: dict) -> dict:
        """发送 HTTP 请求"""
        url = f"{self.base_url}/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise Exception(f"API Error {e.code}: {error_body}")

    def messages(self):
        return MiniMaxMessages(self)


class MiniMaxMessages:
    """MiniMax 消息接口"""

    def __init__(self, client: MiniMaxLLMClient):
        self.client = client

    def create(self, model: str, max_tokens: int, messages: list) -> Any:
        """
        创建消息

        参数：
        - model: 模型名称
        - max_tokens: 最大 token 数
        - messages: 消息列表 [{"role": "user", "content": "..."}]
        """
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }

        result = self.client._make_request(payload)

        # 解析响应 - 处理 thinking 和 text 两种内容块
        content_blocks = result.get("content", [])
        text_output = ""
        for block in content_blocks:
            if block.get("type") == "text":
                text_output = block.get("text", "")
                break
            elif block.get("type") == "thinking":
                # 跳过 thinking 块
                continue

        class Response:
            content = [type('ContentBlock', (object,), {'text': text_output})]

        return Response()


def create_llm_client() -> Any:
    """
    创建 LLM 客户端

    优先级：
    1. MiniMax API（如果配置了 ANTHROPIC_API_KEY）
    2. Mock 客户端（用于测试）
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL")

    if api_key:
        try:
            return MiniMaxLLMClient(api_key=api_key, base_url=base_url)
        except Exception as e:
            print(f"[Warning] Failed to create MiniMax client: {e}, using mock")
            return MockLLMClient()
    else:
        print("[Info] No ANTHROPIC_API_KEY found, using mock client")
        return MockLLMClient()


def get_generator(llm_client=None) -> ContentGenerator:
    """获取生成器实例"""
    return ContentGenerator(llm_client)
