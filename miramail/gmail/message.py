# --------------------------------------------------------------------------------
# Source: https://github.com/jeremyephron/simplegmail
# By: jeremyephron
#
# This code is used in accordance with the repository's license, and this reference
# serves as an acknowledgment of the original author's contribution to this project.
#
# Note that the code below is modified from the original source.
# --------------------------------------------------------------------------------

from typing import List, Optional, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from pydantic import BaseModel, ConfigDict, Field

from . import label
from .attachment import Attachment
from .label import Label


class Message(BaseModel):
    """
    The Message class for emails in your Gmail mailbox. This class should not
    be manually constructed. Contains all information about the associated
    message, and can be used to modify the message's labels (e.g., marking as
    read/unread, archiving, moving to trash, starring, etc.).
    """

    service: "Resource" = Field(
        description="The Gmail service object.",
    )
    creds: Credentials = Field(description="The credentials for the account.")
    user_id: str = Field(
        description="The username of the account the message belongs to"
    )
    id: str = Field(description="The message id.")
    thread_id: str = Field(description="The thread id of the message.")
    recipient: str = Field(description="Who the message was addressed to.")
    sender: str = Field(description="Who the message was sent from.")
    subject: str = Field(description="The subject line of the message.")
    date: str = Field(description="The date the message was sent.")
    snippet: str = Field(description="The snippet line for the message.")
    plain: Optional[str] = Field(
        description="The plaintext contents of the message.", default=None
    )
    html: Optional[str] = Field(
        description="The HTML contents of the message.", default=None
    )
    label_ids: Optional[list[str]] = Field(
        description="The ids of labels associated with this message.", default=None
    )
    attachments: Optional[list[Attachment]] = Field(
        description="A list of attachments for the message.", default=None
    )
    headers: dict = Field(description="A dict of header values.")
    cc: Optional[list[str]] = Field(
        description="Who the message was cc'd on the message.", default=None
    )
    bcc: Optional[list[str]] = Field(
        description="Who the message was bcc'd on the message.", default=None
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _service(self) -> Resource:
        if self.creds.expired:
            self.creds.refresh(Request())

        return self.service

    def __repr__(self) -> str:
        """Represents the object by its sender, recipient, and id."""

        return f"Message(to: {self.recipient}, from: {self.sender}, id: {self.id})"

    def mark_as_read(self) -> None:
        """
        Marks this message as read (by removing the UNREAD label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.remove_label(label.UNREAD)

    def mark_as_unread(self) -> None:
        """
        Marks this message as unread (by adding the UNREAD label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.add_label(label.UNREAD)

    def mark_as_spam(self) -> None:
        """
        Marks this message as spam (by adding the SPAM label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.add_label(label.SPAM)

    def mark_as_not_spam(self) -> None:
        """
        Marks this message as not spam (by removing the SPAM label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.remove_label(label.SPAM)

    def mark_as_important(self) -> None:
        """
        Marks this message as important (by adding the IMPORTANT label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.add_label(label.IMPORTANT)

    def mark_as_not_important(self) -> None:
        """
        Marks this message as not important (by removing the IMPORTANT label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.remove_label(label.IMPORTANT)

    def star(self) -> None:
        """
        Stars this message (by adding the STARRED label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.add_label(label.STARRED)

    def unstar(self) -> None:
        """
        Unstars this message (by removing the STARRED label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.remove_label(label.STARRED)

    def move_to_inbox(self) -> None:
        """
        Moves an archived message to your inbox (by adding the INBOX label).

        """

        self.add_label(label.INBOX)

    def archive(self) -> None:
        """
        Archives the message (removes from inbox by removing the INBOX label).

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.remove_label(label.INBOX)

    def trash(self) -> None:
        """
        Moves this message to the trash.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        try:
            res = (
                self._service.users()
                .messages()
                .trash(
                    userId=self.user_id,
                    id=self.id,
                )
                .execute()
            )

        except HttpError as error:
            # Pass error along
            raise error

        else:
            assert (
                label.TRASH in res["labelIds"]
            ), "An error occurred in a call to `trash`."

            self.label_ids = res["labelIds"]

    def untrash(self) -> None:
        """
        Removes this message from the trash.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        try:
            res = (
                self._service.users()
                .messages()
                .untrash(
                    userId=self.user_id,
                    id=self.id,
                )
                .execute()
            )

        except HttpError as error:
            # Pass error along
            raise error

        else:
            assert (
                label.TRASH not in res["labelIds"]
            ), "An error occurred in a call to `untrash`."

            self.label_ids = res["labelIds"]

    def move_from_inbox(self, to: Union[Label, str]) -> None:
        """
        Moves a message from your inbox to another label "folder".

        Args:
            to: The label to move to.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.modify_labels(to, label.INBOX)

    def add_label(self, to_add: Union[Label, str]) -> None:
        """
        Adds the given label to the message.

        Args:
            to_add: The label to add.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.modify_labels(to_add, [])

    def add_labels(self, to_add: Union[List[Label], List[str]]) -> None:
        """
        Adds the given labels to the message.

        Args:
            to_add: The list of labels to add.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.modify_labels(to_add, [])

    def remove_label(self, to_remove: Union[Label, str]) -> None:
        """
        Removes the given label from the message.

        Args:
            to_remove: The label to remove.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.modify_labels([], to_remove)

    def remove_labels(self, to_remove: Union[List[Label], List[str]]) -> None:
        """
        Removes the given labels from the message.

        Args:
            to_remove: The list of labels to remove.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        self.modify_labels([], to_remove)

    def modify_labels(
        self,
        to_add: Union[Label, str, List[Label], List[str]],
        to_remove: Union[Label, str, List[Label], List[str]],
    ) -> None:
        """
        Adds or removes the specified label.

        Args:
            to_add: The label or list of labels to add.
            to_remove: The label or list of labels to remove.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """
        list_add: Union[List[Label], List[str]] = []
        list_remove: Union[List[Label], List[str]] = []

        if isinstance(to_add, Label):
            list_add = [to_add]
        elif isinstance(to_add, str):  # make mypy happy
            list_add = [to_add]

        if isinstance(to_remove, Label):
            list_remove = [to_remove]
        elif isinstance(to_remove, str):  # make mypy happy
            list_remove = [to_remove]

        try:
            res = (
                self._service.users()
                .messages()
                .modify(
                    userId=self.user_id,
                    id=self.id,
                    body=self._create_update_labels(list_add, list_remove),
                )
                .execute()
            )

        except HttpError as error:
            # Pass along error
            raise error

        else:
            assert all([lbl in res["labelIds"] for lbl in to_add]) and all(
                [lbl not in res["labelIds"] for lbl in to_remove]
            ), "An error occurred while modifying message label."

            self.label_ids = res["labelIds"]

    def _create_update_labels(
        self,
        to_add: Optional[Union[List[Label], List[str]]] = None,
        to_remove: Optional[Union[List[Label], List[str]]] = None,
    ) -> dict:
        """
        Creates an object for updating message label.

        Args:
            to_add: A list of labels to add.
            to_remove: A list of labels to remove.

        Returns:
            The modify labels object to pass to the Gmail API.

        """

        if to_add is None:
            to_add = []

        if to_remove is None:
            to_remove = []

        return {
            "addLabelIds": [
                lbl.id if isinstance(lbl, Label) else lbl for lbl in to_add
            ],
            "removeLabelIds": [
                lbl.id if isinstance(lbl, Label) else lbl for lbl in to_remove
            ],
        }
