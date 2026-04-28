"""配置加载模块"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ChapterWordCount:
    min: int
    max: int


@dataclass
class Config:
    model: str
    max_tokens: int
    chapter_word_count: Dict[str, ChapterWordCount]
    summary_buffer_size: int
    recent_chapters_in_context: int
    sandbox_timeout: int
    subagent_timeout: int
    style_warning_threshold: int


def load_config(config_path: str = "CONFIG.md") -> Config:
    """从 CONFIG.md 加载配置"""
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 简单解析 YAML 格式的配置
    data = yaml.safe_load(content)

    chapter_configs = {}
    for chapter_type, counts in data.get("chapter_word_count", {}).items():
        chapter_configs[chapter_type] = ChapterWordCount(
            min=counts["min"],
            max=counts["max"]
        )

    return Config(
        model=data.get("model", "claude-sonnet-4-7"),
        max_tokens=data.get("max_tokens", 8192),
        chapter_word_count=chapter_configs,
        summary_buffer_size=data.get("summary_buffer_size", 10),
        recent_chapters_in_context=data.get("recent_chapters_in_context", 3),
        sandbox_timeout=data.get("sandbox_timeout", 90),
        subagent_timeout=data.get("subagent_timeout", 90),
        style_warning_threshold=data.get("style_warning_threshold", 3),
    )


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent


def load_markdown_file(filename: str) -> str:
    """加载 Markdown 文件"""
    root = get_project_root()
    filepath = root / filename
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return ""
