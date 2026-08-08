import json
import smtplib
from email.message import EmailMessage
from urllib import error, request

from core.interfaces.agent import Tool


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
            )
        raise ValueError(f"Unsupported communication channel: {channel}")

    def _send_webhook(self, target: str, message: str, timeout_seconds: float):
        payload = json.dumps({"message": message}).encode("utf-8")
        req = request.Request(
            target,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as resp:
                return {"status": "sent", "http_status": resp.status}
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            return {"status": "error", "http_status": exc.code, "details": details}
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

        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(email_msg)

        return {"status": "sent", "channel": "email", "recipient": recipient}
