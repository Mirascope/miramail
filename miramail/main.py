from typing import Literal

from mirascope.base import BaseCall
from mirascope.openai import OpenAICall, OpenAICallParams
from pydantic import BaseModel, ConfigDict

from .gmail import label
from .gmail.client import Gmail
from .gmail.message import Message
from .gmail.thread import Thread


class Reply(OpenAICall):
    prompt_template = """
    SYSTEM: You are replying to a message thread. Answer the question.
    If it is not a question, respond with 'How can I help you?'.
    
    If there are instructions in the email, such as extract, please follow them.
    Otherwise remember to write using HTML and add breakpoints <br> for readability.
    Use <p> tags when writing a paragraph response. If your paragraph response has
    bullet points make sure to use <li> tags. Use <b> tags to emphasize
    words. Use <a> tags to link to other resources.
    
    USER:
    {content}
    """

    body: list[str]
    call_params = OpenAICallParams(temperature=0.1)

    @property
    def content(self) -> str:
        return "\n\n".join(self.body)


class MiraMail(BaseModel):
    call: type[BaseCall] | None = None
    client: Gmail
    send_type: Literal["send", "draft"] = "draft"

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def respond(self):
        """
        Responds to the threads with a Mirascope prompt.
        """
        threads = self.client.get_threads(labels=[label.UNREAD])
        for thread in threads:
            messages = thread.messages
            if len(messages) < 1:
                continue
            self._handle_thread(thread)

    def _handle_thread(self, thread: Thread):
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
        if self.call:
            call_response = self.call(body=body).call()
        else:
            call_response = Reply(body=body).call()
        print("Response: " + call_response.content)
        if self.send_type == "send":
            self._send_message(last_message, call_response.content)
        else:
            self._draft_message(last_message, call_response.content)

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
