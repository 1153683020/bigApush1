"""多渠道消息通知（飞书 + 企业微信）

统一入口，自动读取配置（环境变量优先，其次 config/config.yaml），
同时向所有已配置的渠道发送消息。

环境变量：
    FEISHU_WEBHOOK   飞书机器人 webhook URL
    FEISHU_SECRET    飞书机器人加签密钥（可选，开启"签名校验"时必填）
    WECOM_WEBHOOK    企业微信机器人 webhook URL
"""
import logging
import os

logger = logging.getLogger(__name__)


class MultiNotifier:
    """同时向所有已配置渠道（飞书/企业微信）发送消息"""

    def __init__(self, feishu=None, wecom=None):
        self.notifiers = []
        if feishu is not None:
            self.notifiers.append(feishu)
        if wecom is not None:
            self.notifiers.append(wecom)

    @classmethod
    def from_config(cls, config: dict = None, config_path: str = "config/config.yaml") -> "MultiNotifier":
        """环境变量优先，其次配置文件。config 为空时尝试读取配置文件"""
        cfg = dict(config) if config else {}
        if not cfg:
            try:
                import yaml
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning("读取配置文件失败，仅使用环境变量: %s", e)

        feishu_cfg = cfg.get("feishu") or {}
        wecom_cfg = cfg.get("wecom") or {}

        feishu_webhook = os.environ.get("FEISHU_WEBHOOK") or feishu_cfg.get("webhook_url", "")
        feishu_secret = os.environ.get("FEISHU_SECRET") or feishu_cfg.get("secret", "")
        wecom_webhook = os.environ.get("WECOM_WEBHOOK") or wecom_cfg.get("webhook_url", "")

        feishu = None
        if feishu_webhook:
            from utils.feishu_notifier import FeishuNotifier
            feishu = FeishuNotifier(feishu_webhook, feishu_secret)

        wecom = None
        if wecom_webhook:
            from utils.wecom_notifier import WeComNotifier
            wecom = WeComNotifier(wecom_webhook)

        return cls(feishu=feishu, wecom=wecom)

    @property
    def enabled(self) -> bool:
        return bool(self.notifiers)

    def send_text(self, text: str) -> bool:
        """发送纯文本消息，返回是否所有渠道发送成功"""
        if not self.notifiers:
            logger.warning("未配置任何通知渠道（飞书/企业微信）")
            return False
        ok = True
        for n in self.notifiers:
            ok = n.send_text(text) and ok
        return ok

    def send_post(self, title: str, content_lines: list) -> bool:
        """发送富文本消息（企业微信侧以 markdown 发送）"""
        if not self.notifiers:
            logger.warning("未配置任何通知渠道（飞书/企业微信）")
            return False
        ok = True
        for n in self.notifiers:
            ok = n.send_post(title, content_lines) and ok
        return ok


def send_text(text: str) -> bool:
    """便捷函数：使用环境变量/配置文件发送纯文本"""
    return MultiNotifier.from_config().send_text(text)


def send_post(title: str, content_lines: list) -> bool:
    """便捷函数：使用环境变量/配置文件发送富文本"""
    return MultiNotifier.from_config().send_post(title, content_lines)
