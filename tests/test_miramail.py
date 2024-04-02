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
@patch.object(Gmail, "create_draft", return_value=MagicMock())
@patch.object(Gmail, "send_message", return_value=MagicMock())
def test_respond(
    send_message_mock,
    create_draft_mock,
    modify_labels_mock,
    messages: list[Message],
    send_type: Literal["send", "draft"],
):
    miramail = MiraMail(client=MagicMock(spec=Gmail), send_type=send_type)
    thread1 = MagicMock(spec=Thread)
    thread1.messages = messages
    miramail.client.get_threads.return_value = [thread1]

    def handle_body_mock(body):
        return "test"

    miramail.respond(handle_body_mock)

    miramail.client.get_threads.assert_called_once_with(labels=["UNREAD"])
