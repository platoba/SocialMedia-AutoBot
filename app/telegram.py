"""Telegram Bot API wrapper with retry and error handling."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class TelegramBot:
    """Lightweight Telegram Bot API client."""

    def __init__(self, api_url: str, timeout: int = 35):
        self.api_url = api_url
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method: str, params: Optional[dict] = None,
                 data: Optional[dict] = None) -> Optional[dict]:
        try:
            if data:
                r = self.session.post(
                    f"{self.api_url}/{method}", data=data, timeout=self.timeout
                )
            else:
                r = self.session.get(
                    f"{self.api_url}/{method}", params=params, timeout=self.timeout
                )
            result = r.json()
            if not result.get("ok"):
                logger.warning("API %s failed: %s", method, result.get("description"))
            return result
        except requests.RequestException as e:
            logger.error("API %s error: %s", method, e)
            return None

    def get_me(self) -> Optional[dict]:
        return self._request("getMe")

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> Optional[dict]:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        return self._request("getUpdates", params=params)

    def send_message(self, chat_id: int, text: str,
                     reply_to: Optional[int] = None,
                     parse_mode: str = "Markdown") -> Optional[dict]:
        params = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
        if parse_mode:
            params["parse_mode"] = parse_mode

        result = self._request("sendMessage", params=params)
        # Fallback without parse_mode if Markdown fails
        if not result or not result.get("ok"):
            params.pop("parse_mode", None)
            result = self._request("sendMessage", params=params)
        return result

    def send_photo(self, chat_id: int, photo_url: str,
                   caption: str = "", reply_to: Optional[int] = None) -> Optional[dict]:
        params = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:1024],
        }
        if reply_to:
            params["reply_to_message_id"] = reply_to
        return self._request("sendPhoto", params=params)

    def send_callback_answer(self, callback_id: str, text: str = "") -> Optional[dict]:
        return self._request("answerCallbackQuery", params={
            "callback_query_id": callback_id,
            "text": text,
        })
