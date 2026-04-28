"""Mailbox 点对点通信机制"""
import os
import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from core.config import get_project_root


@dataclass
class MailboxMessage:
    """邮箱消息"""
    id: str
    sender: str
    recipient: str
    message_type: str
    task_id: str
    payload: Dict[str, Any]
    timestamp: str
    status: str = "pending"  # pending, read, processed


class Mailbox:
    """
    Mailbox 通信机制

    outbox/: 主控 Agent 投递任务
    inbox/: Subagent 写回结果

    消息格式：
    {
        "id": "msg_xxx",
        "sender": "orchestrator",
        "recipient": "lore_verifier",
        "message_type": "verify_lore",
        "task_id": "task_xxx",
        "payload": {...},
        "timestamp": "ISO8601",
        "status": "pending"
    }
    """

    def __init__(self):
        self.root = get_project_root()
        self.outbox = self.root / "mailbox" / "outbox"
        self.inbox = self.root / "mailbox" / "inbox"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保邮箱目录存在"""
        self.outbox.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)

    def send_message(
        self,
        sender: str,
        recipient: str,
        message_type: str,
        payload: Dict[str, Any]
    ) -> str:
        """
        发送消息到 outbox

        返回：消息 ID
        """
        msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        message = MailboxMessage(
            id=msg_id,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            task_id=task_id,
            payload=payload,
            timestamp=datetime.now().isoformat()
        )

        # 写入 outbox
        filename = f"{msg_id}_{recipient}.json"
        filepath = self.outbox / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "id": message.id,
                "sender": message.sender,
                "recipient": message.recipient,
                "message_type": message.message_type,
                "task_id": message.task_id,
                "payload": message.payload,
                "timestamp": message.timestamp,
                "status": message.status
            }, f, ensure_ascii=False, indent=2)

        return task_id

    def wait_for_response(
        self,
        task_id: str,
        sender: str,
        timeout: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        等待 Subagent 响应

        参数：
        - task_id: 任务 ID（用于匹配响应）
        - sender: 期望的发送方
        - timeout: 超时时间（秒）

        返回：响应 payload 或 None
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 扫描 inbox 中匹配的消息
            for filepath in self.inbox.glob("*.json"):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        msg = json.load(f)

                    # 检查是否匹配
                    if msg.get("task_id") == task_id and msg.get("sender") == sender:
                        # 处理完成后删除文件
                        filepath.unlink()
                        return msg.get("payload")
                except (json.JSONDecodeError, FileNotFoundError):
                    continue

            # 轮询间隔
            time.sleep(0.5)

        return None

    def poll_inbox(self, recipient: str) -> List[Dict[str, Any]]:
        """
        轮询 inbox，获取所有发给指定收件人的消息

        返回：消息列表
        """
        messages = []
        pattern = f"*_{recipient}.json"

        for filepath in self.inbox.glob(pattern):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    msg = json.load(f)
                messages.append(msg)
            except (json.JSONDecodeError, FileNotFoundError):
                continue

        return messages

    def mark_processed(self, message_id: str) -> None:
        """标记消息为已处理"""
        for filepath in self.inbox.glob(f"{message_id}_*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    msg = json.load(f)
                msg["status"] = "processed"
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(msg, f, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, FileNotFoundError):
                continue


def get_mailbox() -> Mailbox:
    """获取 Mailbox 实例"""
    return Mailbox()
