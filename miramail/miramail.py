"""
Miramail is a convenience library for Mirascope with an email interface.
"""
from typing import Callable, Literal
from pydantic import BaseModel, ConfigDict

from .gmail import label
from .gmail.client import Gmail
from .gmail.message import Message
from .gmail.thread import Thread

class MiraMail(BaseModel):
    client: Gmail
    send_type: Literal["send", "draft"] = "draft"

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def respond(self, handle_body: Callable[[list[str]], str]):
        """
        Responds to the threads with a Mirascope prompt.
        """
        threads = self.client.get_threads(labels=[label.UNREAD])
        for thread in threads:
            messages = thread.messages
            if len(messages) < 1:
                continue
            self._handle_thread(thread, handle_body)

    def _handle_thread(self, thread: Thread, handle_body: Callable[[list[str]], str]):
        """Handles a thread.

        Args:
            thread: The thread to handle.
        """
        body = []
        messages = thread.messages
        for message in messages:
            if message.html:
                body.append(message.html)
            elif message.plain:
                body.append(message.plain)
        last_message = messages[-1]
        print("From: " + last_message.sender)
        print("Snippet: " + last_message.snippet)
        content = handle_body(body)
        print("Response: " + content)
        if self.send_type == "send":
            self._send_message(last_message, content)
        else:
            self._draft_message(last_message, content)

    def _send_message(self, message: Message, content: str):
        """Responds to the thread.

        Args:
            message: The message to draft.
            content: The content of the message.
        """

        self.client.send_message(
            sender=message.sender,
            to=message.recipient,
            subject=message.subject,
            msg_html=content,
            thread_id=message.thread_id,
            in_reply_to=message.id,
        )
        message.mark_as_read()

    def _draft_message(self, message: Message, content: str):
        """Drafts a message.

        Args:
            message: The message to draft.
            content: The content of the message.
        """
        self.client.create_draft(
            sender=message.sender,
            to=message.recipient,
            subject=message.subject,
            msg_html=content,
            thread_id=message.thread_id,
            in_reply_to=message.id,
        )
        message.mark_as_read()
