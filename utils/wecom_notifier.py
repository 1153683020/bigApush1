"""企业微信机器人通知

说明：在企业微信群中添加群机器人，复制 webhook URL（形如
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx）。
企业微信对单条消息内容有字节上限（text 2048 字节、markdown 4096 字节），
超长内容会自动按行拆分为多条发送。
"""
import logging

import requests

logger = logging.getLogger(__name__)

CONTENT_LIMITS = {"text": 2048, "markdown": 4096}


class WeComNotifier:
    def __init__(self, webhook_url: str = ""):
        self.webhook_url = webhook_url

    def _post(self, payload: dict) -> bool:
        if not self.webhook_url:
            logger.warning("企业微信 webhook_url 未配置")
            return False
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            result = resp.json()
            if result.get("errcode") == 0:
                logger.info("企业微信推送成功")
                return True
            logger.error("企业微信推送失败: %s", result)
            return False
        except Exception as e:
            logger.error("企业微信推送异常: %s", e)
            return False

    @staticmethod
    def _split_content(content: str, limit: int) -> list:
        """按行拆分超长内容，保证每段不超过字节上限"""
        if len(content.encode("utf-8")) <= limit:
            return [content]
        chunks, buf, buf_len = [], [], 0
        for line in content.splitlines():
            if len(line.encode("utf-8")) > limit:
                line = line.encode("utf-8")[: limit - 3].decode("utf-8", errors="ignore") + "..."
            line_len = len(line.encode("utf-8"))
            if buf and buf_len + line_len + 1 > limit:
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            buf.append(line)
            buf_len += line_len + 1
        if buf:
            chunks.append("\n".join(buf))
        return chunks

    def send_text(self, text: str) -> bool:
        if not self.webhook_url:
            logger.warning("企业微信 webhook_url 未配置")
            return False
        ok = True
        for content in self._split_content(text, CONTENT_LIMITS["text"]):
            ok = self._post({"msgtype": "text", "text": {"content": content}}) and ok
        return ok

    def send_markdown(self, content: str) -> bool:
        if not self.webhook_url:
            logger.warning("企业微信 webhook_url 未配置")
            return False
        ok = True
        for chunk in self._split_content(content, CONTENT_LIMITS["markdown"]):
            ok = self._post({"msgtype": "markdown", "markdown": {"content": chunk}}) and ok
        return ok

    def send_post(self, title: str, content_lines: list) -> bool:
        """兼容飞书 notifier 接口，以 markdown 格式发送"""
        content = "\n".join(content_lines)
        if title:
            content = f"## {title}\n{content}"
        return self.send_markdown(content)
