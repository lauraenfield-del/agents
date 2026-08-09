import json
import ssl
import smtplib
from email.message import EmailMessage
from urllib import error, request

from core.interfaces.agent import Tool
from core.tools.web import _validate_url_for_ssrf, _build_ssrf_safe_opener as build_ssrf_safe_opener


class CommunicationTool(Tool):
    @property
    def name(self) -> str:
        return "communication"

    @property
    def description(self) -> str:
        return "Sends outbound communications via HTTP webhooks or SMTP email."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "enum": ["webhook", "email"]},
                "target": {"type": "string"},
                "message": {"type": "string"},
                "subject": {"type": "string"},
                "smtp_host": {"type": "string"},
                "smtp_port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "smtp_username": {"type": "string"},
                "smtp_password": {"type": "string"},
                "sender": {"type": "string"},
                "timeout_seconds": {"type": "number", "minimum": 1, "maximum": 60},
            },
            "required": ["channel", "target", "message"],
            "additionalProperties": False,
        }

    def execute(
        self,
        channel: str,
        target: str,
        message: str,
        subject: str = "Agent Message",
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_username: str | None = None,
        smtp_password: str | None = None,
        sender: str | None = None,
        timeout_seconds: float = 20,
    ):
        if channel == "webhook":
            return self._send_webhook(target=target, message=message, timeout_seconds=timeout_seconds)
        if channel == "email":
            return self._send_email(
                recipient=target,
                message=message,
                subject=subject,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_username=smtp_username,
                smtp_password=smtp_password,
                sender=sender,
                timeout_seconds=timeout_seconds,
            )
        raise ValueError(f"Unsupported communication channel: {channel}")

    def _send_webhook(self, target: str, message: str, timeout_seconds: float):
        err = _validate_url_for_ssrf(target)
        if err:
            return {"status": "error", "details": f"Blocked target: {err}"}

        payload = json.dumps({"message": message}).encode("utf-8")
        req = request.Request(
            target,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = build_ssrf_safe_opener()
        try:
            with opener.open(req, timeout=timeout_seconds) as resp:
                return {"status": "sent", "http_status": resp.status}
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            return {"status": "error", "http_status": exc.code, "details": details[:2000]}
        except error.URLError as exc:
            return {"status": "error", "details": str(exc.reason)}

    def _send_email(
        self,
        recipient: str,
        message: str,
        subject: str,
        smtp_host: str | None,
        smtp_port: int,
        smtp_username: str | None,
        smtp_password: str | None,
        sender: str | None,
        timeout_seconds: float = 20,
    ):
        if not smtp_host or not smtp_username or not smtp_password or not sender:
            raise ValueError(
                "smtp_host, smtp_username, smtp_password, and sender are required for email channel."
            )

        email_msg = EmailMessage()
        email_msg["From"] = sender
        email_msg["To"] = recipient
        email_msg["Subject"] = subject
        email_msg.set_content(message)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_seconds) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(email_msg)

        return {"status": "sent", "channel": "email", "recipient": recipient}
