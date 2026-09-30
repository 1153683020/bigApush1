"""飞书机器人通知（支持 webhook 加签）

加签说明（飞书官方文档）：
    如机器人开启了"签名校验"，需要以 timestamp 作为 HmacSHA256 的 msg，
    以 "{timestamp}\n{secret}" 作为 key，将签名结果 base64 编码后，
    以 timestamp 和 sign 参数追加到 webhook URL 中。
"""
import base64
import hashlib
import hmac
import logging
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

logger = logging.getLogger(__name__)


def gen_sign(secret: str, timestamp: int = None) -> tuple:
    """生成飞书自定义机器人加签参数，返回 (timestamp, sign)"""
    if timestamp is None:
        timestamp = int(time.time())
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return timestamp, sign


def sign_webhook_url(webhook_url: str, secret: str) -> str:
    """为 webhook URL 追加加签参数，secret 为空时原样返回"""
    if not secret:
        return webhook_url
    timestamp, sign = gen_sign(secret)
    parsed = urlparse(webhook_url)
    query = dict(parse_qsl(parsed.query))
    query["timestamp"] = str(timestamp)
    query["sign"] = sign
    return urlunparse(parsed._replace(query=urlencode(query)))


class FeishuNotifier:
    def __init__(self, webhook_url: str = "", secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret

    def _post(self, payload: dict) -> bool:
        if not self.webhook_url:
            logger.warning("飞书 webhook_url 未配置")
            return False
        url = sign_webhook_url(self.webhook_url, self.secret)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                logger.info("飞书推送成功")
                return True
            logger.error("飞书推送失败: %s", result)
            return False
        except Exception as e:
            logger.error("飞书推送异常: %s", e)
            return False

    def send_text(self, text: str) -> bool:
        if not self.webhook_url:
            logger.warning("飞书 webhook_url 未配置")
            return False
        return self._post({"msg_type": "text", "content": {"text": text}})

    def send_post(self, title: str, content_lines: list) -> bool:
        if not self.webhook_url:
            logger.warning("飞书 webhook_url 未配置")
            return False
        post_content = []
        for line in content_lines:
            post_content.append([{"tag": "text", "text": line}])
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": post_content
                    }
                }
            }
        }
        return self._post(payload)
