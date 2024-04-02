"""Test Miramail"""

from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource

from miramail.gmail.client import Gmail
from miramail.gmail.message import Message
from miramail.gmail.thread import Thread
from miramail.miramail import MiraMail


@pytest.mark.parametrize(
    "send_type",
    [
        "send",
        "draft",
    ],
)
@pytest.mark.parametrize(
    "messages",
    [
        [
            Message(
                service=MagicMock(spec=Resource),
                creds=MagicMock(spec=Credentials),
                user_id="test_user",
                id="test_message_id",
                thread_id="test_thread_id",
                recipient="test@example.com",
                sender="sender@example.com",
                subject="Test Subject",
                date="2023-06-01",
                snippet="Test message snippet",
                html="<p>Test HTML body</p>",
                headers={},
                label_ids=["INBOX", "UNREAD"],
            )
        ],
        [
            Message(
                service=MagicMock(spec=Resource),
                creds=MagicMock(spec=Credentials),
                user_id="test_user",
                id="test_message_id",
                thread_id="test_thread_id",
                recipient="test@example.com",
                sender="sender@example.com",
                subject="Test Subject",
                date="2023-06-01",
                snippet="Test message snippet",
                plain="Test plain text body",
                headers={},
                label_ids=["INBOX", "UNREAD"],
            )
        ],
        [],
    ],
)
@patch.object(Message, "modify_labels", return_value=MagicMock())
def test_respond(
    get_threads_mock: MagicMock,
    messages: list[Message],
    send_type: Literal["send", "draft"],
):
    gmail = MagicMock(spec=Gmail, send_type=send_type)
    gmail.send_message = MagicMock()
    gmail.create_draft = MagicMock()

    thread1 = MagicMock(spec=Thread)
    thread1.messages = messages

    gmail.get_threads = MagicMock(return_value=[thread1])
    miramail = MiraMail(client=gmail, send_type=send_type)

    def handle_body_mock(body: list[str]):
        return "\n".join(body)

    miramail.respond(handle_body_mock)

    gmail.get_threads.assert_called_once_with(labels=["UNREAD"])
