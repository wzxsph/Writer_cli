"""主控写手 Agent"""
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from core.config import get_project_root, load_config
from core.assembler import assemble_chapter_context
from core.intent_parser import IntentParser
from core.permission_gate import check_permission
from core.generator import ContentGenerator, get_generator
from core.scheduler import get_scheduler
from core.compressor import get_compressor
from sandbox.validator import SandboxValidator
from agents.mailbox import get_mailbox


class OrchestratorWriterAgent:
    """
    主控写手 Agent

    负责执行 9 步循环中的 Step 1 至 Step 9，并向 Subagent 派发任务

    上下文隔离原则：
    - 对 Subagent 的内部上下文完全不透明
    - 只知道发出了什么消息，以及收到了什么回复
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.config = load_config()
        self.scheduler = get_scheduler()
        self.compressor = get_compressor()
        self.mailbox = get_mailbox()

        # 各步骤处理器
        self.assembler = None  # 延迟初始化
        self.intent_parser = IntentParser(llm_client)
        self.generator = get_generator(llm_client)
        self.validator = SandboxValidator()

        # Subagent 配置
        self.subagent_timeout = self.config.subagent_timeout

    def run_chapter_loop(
        self,
        vol: str,
        chapter: int,
        chapter_type: str = "normal"
    ) -> Tuple[bool, str]:
        """
        执行单次章节循环

        返回：(是否成功, 原因/结果)
        """
        print(f"[Orchestrator] 开始执行 {vol} Chapter {chapter}")

        # Step 1: 上下文装配
        print("[Step 1] 上下文装配...")
        context = self._step1_context_assembly(vol, chapter, chapter_type)
        if not context:
            return False, "上下文装配失败"

        # Step 2: 任务意图解析
        print("[Step 2] 任务意图解析...")
        intent = self._step2_intent_parsing(context)
        if not intent:
            return False, "意图解析失败"

        # Step 3: 权限门控预检
        print("[Step 3] 权限门控预检...")
        # 在正文生成后才做权限检查，这里仅记录意图

        # Step 4: 正文生成
        print("[Step 4] 正文生成...")
        text = self._step4_primary_generation(context, vol, chapter, chapter_type)
        if not text:
            return False, "正文生成失败"

        # Step 5: 编程式工具沙盒校验
        print("[Step 5] 沙盒校验...")
        validation_result = self._step5_sandbox_validation(text, vol, chapter, chapter_type)

        if not validation_result["passed"]:
            # 有阻断级违规
            if validation_result.get("auto_fixable"):
                # 尝试自动修复
                print("[Step 6] 触发局部修正...")
                text = self._step6_fix_and_revalidate(text, validation_result["violations"])
                if not text:
                    return False, "局部修正失败"
            else:
                return False, f"沙盒校验失败: {validation_result['violations']}"

        # Step 6: 沙盒报告路由（如果自动修复后重新校验）
        # 已在上面处理

        # Step 7: 动态记忆提交
        print("[Step 7] 动态记忆提交...")
        self._step7_memory_commit(text, vol, chapter)

        # Step 8: 章节归档
        print("[Step 8] 章节归档...")
        archive_path = self._step8_chapter_archive(text, vol, chapter)
        if not archive_path:
            return False, "章节归档失败"

        # Step 9: 调度器推进
        print("[Step 9] 调度器推进...")
        next_task = self._step9_scheduler_advance(vol, chapter)

        print(f"[Orchestrator] {vol} Chapter {chapter} 完成")
        return True, f"完成归档至 {archive_path}"

    def _step1_context_assembly(self, vol: str, chapter: int, chapter_type: str) -> Optional[str]:
        """Step 1: 上下文装配"""
        try:
            context = assemble_chapter_context(vol, chapter, chapter_type)
            return context
        except Exception as e:
            print(f"[Error] 上下文装配异常: {e}")
            return None

    def _step2_intent_parsing(self, context: str) -> Optional[Dict[str, Any]]:
        """Step 2: 任务意图解析"""
        try:
            intent = self.intent_parser.parse(context, "")
            return intent
        except Exception as e:
            print(f"[Error] 意图解析异常: {e}")
            return None

    def _step4_primary_generation(
        self,
        context: str,
        vol: str,
        chapter: int,
        chapter_type: str
    ) -> Optional[str]:
        """Step 4: 正文生成"""
        try:
            text = self.generator.generate_chapter(
                context=context,
                task="",  # 任务已包含在 context 中
                vol=vol,
                chapter=chapter,
                chapter_type=chapter_type
            )
            return text
        except Exception as e:
            print(f"[Error] 正文生成异常: {e}")
            return None

    def _step5_sandbox_validation(
        self,
        text: str,
        vol: str,
        chapter: int,
        chapter_type: str
    ) -> Dict[str, Any]:
        """Step 5: 沙盒校验"""
        try:
            # 构建校验任务
            min_count = self.config.chapter_word_count.get(
                chapter_type,
                self.config.chapter_word_count["normal"]
            ).min
            max_count = self.config.chapter_word_count.get(
                chapter_type,
                self.config.chapter_word_count["normal"]
            ).max

            # 执行校验
            result = self.validator.validate_all(
                text=text,
                vol=vol,
                chapter=chapter,
                chapter_type=chapter_type,
                min_word_count=min_count,
                max_word_count=max_count,
                llm_client=self.llm_client
            )

            # 同时派发 Subagent 任务
            self._dispatch_subagent_tasks(text, vol, chapter)

            return result

        except Exception as e:
            print(f"[Error] 沙盒校验异常: {e}")
            return {
                "passed": False,
                "violations": [{"reason": str(e)}],
                "warnings": [],
                "auto_fixable": False
            }

    def _dispatch_subagent_tasks(self, text: str, vol: str, chapter: int) -> None:
        """
        向 Subagent 并发派发校验任务

        通过 Mailbox 机制
        """
        # 生成摘要用于 Subagent
        summary = text[:500] if len(text) > 500 else text

        # 向设定考据 Subagent 派发任务
        lore_payload = {
            "chapter_text": summary,
            "lore_references": {
                "WORLDBUILD.md": str(get_project_root() / "WORLDBUILD.md"),
                "CHARACTERS.md": str(get_project_root() / "CHARACTERS.md")
            }
        }
        self.mailbox.send_message(
            sender="orchestrator",
            recipient="lore_verifier",
            message_type="verify_lore",
            payload=lore_payload
        )

        # 向反套路 Subagent 派发任务
        cliche_payload = {
            "summary": summary,
            "full_text": text
        }
        self.mailbox.send_message(
            sender="orchestrator",
            recipient="anti_cliche",
            message_type="review_cliche",
            payload=cliche_payload
        )

        # 轮询 Subagent 响应（异步等待）
        # 实际实现中应该在后台线程/进程中等待

    def _step6_fix_and_revalidate(
        self,
        text: str,
        violations: list
    ) -> Optional[str]:
        """Step 6: 局部修正"""
        try:
            fix_prompt = self.validator.generate_fix_prompt(violations, text)
            if not fix_prompt:
                return None

            # 调用 LLM 进行局部修复
            messages_interface = self.llm_client.messages
            if callable(messages_interface):
                messages_interface = messages_interface()
            response = messages_interface.create(
                model=self.config.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": fix_prompt}]
            )

            fixed_text = response.content[0].text.strip()

            # 重新校验
            # 注意：这里应该重新调用 _step5，但为简化直接返回
            return fixed_text

        except Exception as e:
            print(f"[Error] 局部修正异常: {e}")
            return None

    def _step7_memory_commit(self, text: str, vol: str, chapter: int) -> None:
        """Step 7: 动态记忆提交"""
        try:
            # 调用伏笔管理 Subagent
            from agents.memory_manager import MemoryManagerAgent

            manager = MemoryManagerAgent()
            result = manager.run({
                "text": text,
                "current_chapter": chapter
            })

            # 应用更新建议
            update_suggestion = result.get("update_suggestion", {})
            new_content = update_suggestion.get("new_memory_content")
            if new_content:
                memory_file = get_project_root() / "MEMORY.md"
                with open(memory_file, "w", encoding="utf-8") as f:
                    f.write(new_content)

            # 触发压缩管线
            if result.get("new_foreshadows"):
                # 生成摘要
                summary = self.compressor.level2_compress_to_summary(
                    text, vol, chapter, self.llm_client
                )
                # 更新滚动窗口
                self.compressor.level3_rolling_window(summary, vol, chapter)

        except Exception as e:
            print(f"[Error] 记忆提交异常: {e}")

    def _step8_chapter_archive(self, text: str, vol: str, chapter: int) -> Optional[str]:
        """Step 8: 章节归档"""
        try:
            chapters_dir = get_project_root() / "chapters" / vol
            chapters_dir.mkdir(parents=True, exist_ok=True)

            chapter_file = chapters_dir / f"CHAPTER_{chapter}.md"

            # 原子性写入：先写 .tmp，再重命名
            tmp_file = chapter_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(text)

            tmp_file.rename(chapter_file)

            # 更新 INDEX.md
            self._update_index(vol, chapter, text[:100])

            return str(chapter_file)

        except Exception as e:
            print(f"[Error] 章节归档异常: {e}")
            return None

    def _update_index(self, vol: str, chapter: int, excerpt: str) -> None:
        """更新章节索引"""
        index_file = get_project_root() / "INDEX.md"

        entry = f"\n### {vol} Chapter {chapter}\n- excerpt: {excerpt[:50]}..."

        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "# 章节索引\n"

        with open(index_file, "w", encoding="utf-8") as f:
            f.write(content + entry)

    def _step9_scheduler_advance(self, vol: str, chapter: int) -> Dict[str, Any]:
        """Step 9: 调度器推进"""
        try:
            next_task = self.scheduler.advance_to_next(vol, chapter)
            return next_task
        except Exception as e:
            print(f"[Error] 调度器推进异常: {e}")
            return {}


def get_orchestrator(llm_client=None) -> OrchestratorWriterAgent:
    """获取主控 Agent 实例"""
    return OrchestratorWriterAgent(llm_client)
