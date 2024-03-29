# --------------------------------------------------------------------------------
# Source: https://github.com/jeremyephron/simplegmail
# By: jeremyephron
#
# This code is used in accordance with the repository's license, and this reference
# serves as an acknowledgment of the original author's contribution to this project.
#
# Note that the code below is modified from the original source.
# --------------------------------------------------------------------------------

import base64
import html
import math
import mimetypes
import os
import re
import threading
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import dateutil.parser as parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from simplegmail import Gmail as SimpleGmail

from .attachment import Attachment
from .draft import Draft
from .label import Label
from .message import Message
from .schemas import AttachmentMetadata
from .thread import Thread


class Gmail(SimpleGmail):
    """
    The Gmail class which serves as the entrypoint for the Gmail service API.

    Args:
        credentials_file: The path of the user's credentials.json file.
        token_file: The path of the token file (created on first
            call).
        _creds: Custom credentials object.

    Attributes:
        service (googleapiclient.discovery.Resource): The Gmail service object.

    """

    # Allow Gmail to read and write emails, and access settings like aliases.
    _SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.settings.basic",
    ]
    creds: Optional[Credentials] = None
    _service: Optional[Resource] = None

    # If you don't have a client secret file, follow the instructions at:
    # https://developers.google.com/gmail/api/quickstart/python
    # Make sure the client secret file is in the root directory of your app.

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
        _creds: Optional[Credentials] = None,
    ) -> None:
        if _creds:
            self.creds = _creds
        elif os.path.exists(token_file):
            self.creds = Credentials.from_authorized_user_file(token_file, self._SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file, self._SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_file, "w") as token:
                token.write(self.creds.to_json())

        try:
            # Call the Gmail API
            self._service = build("gmail", "v1", credentials=self.creds)

        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            print(f"An error occurred: {error}")

    @property
    def service(self) -> Resource:
        if self.creds and self.creds.expired:
            self.creds.refresh(Request())

        return self._service

    def _get_threads_from_refs(
        self,
        user_id: str,
        thread_refs: list[dict],
        attachments: str = "reference",
        parallel: bool = True,
    ) -> list[Thread]:
        """
        Retrieves the actual threads from a list of references.
        Args:
            user_id: The account the threads belong to.
            thread_refs: A list of thread references with keys id, threadId.
            attachments: Accepted values are 'ignore' which completely ignores
                all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download'
                which downloads the attachment data to store locally. Default
                'reference'.
            parallel: Whether to retrieve threads in parallel. Default true.
                Currently parallelization is always on, since there is no
                reason to do otherwise.
        Returns:
            A list of Thread objects.
        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.
        """

        if not thread_refs:
            return []

        if not parallel:
            return [
                self._build_thread_from_ref(user_id, ref, attachments)
                for ref in thread_refs
            ]

        max_num_threads = 12  # empirically chosen, prevents throttling
        target_thrds_per_thread = 10  # empirically chosen
        num_threads = min(
            math.ceil(len(thread_refs) / target_thrds_per_thread), max_num_threads
        )
        batch_size = math.ceil(len(thread_refs) / num_threads)
        thread_lists: list[list[Thread]] = [[] for _ in range(num_threads)]

        def thread_download_batch(thread_num: int) -> None:
            gmail = Gmail(_creds=self.creds)

            start = thread_num * batch_size
            end = min(len(thread_refs), (thread_num + 1) * batch_size)
            thread_lists[thread_num] = [
                gmail._build_thread_from_ref(user_id, thread_refs[i], attachments)
                for i in range(start, end)
            ]

            gmail.service.close()

        threads = [
            threading.Thread(target=thread_download_batch, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        return sum(thread_lists, [])

    def _build_thread_from_ref(
        self, user_id: str, thread_ref: dict, attachments: str = "reference"
    ) -> Thread:
        """
        Creates a Thread object from a reference.
        Args:
            user_id: The username of the account the thread belongs to.
            thread_ref: The thread reference object returned from the Gmail
                API.
            attachments: Accepted values are 'ignore' which completely ignores
                all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download' which
                downloads the attachment data to store locally. Default
                'reference'.
        Returns:
            The Thread object.
        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.
        """

        try:
            # Get thread JSON
            thread = (
                self.service.users()
                .threads()
                .get(userId=user_id, id=thread_ref["id"])
                .execute()
            )

        except HttpError as error:
            # Pass along the error
            raise error

        else:
            id = thread["id"]
            # snippet = html.unescape(thread['snippet'])
            snippet = ""

            message_refs = []
            if "messages" in thread:  # ensure request was successful
                message_refs.extend(thread["messages"])

            messages = self._get_messages_from_refs(user_id, message_refs, attachments)

            return Thread(user_id=user_id, id=id, snippet=snippet, messages=messages)

    def _get_messages_from_refs(
        self,
        user_id: str,
        message_refs: list[dict],
        attachments: str = "reference",
        parallel: bool = True,
    ) -> list[Message]:
        """
        Retrieves the actual messages from a list of references.

        Args:
            user_id: The account the messages belong to.
            message_refs: A list of message references with keys id, threadId.
            attachments: Accepted values are 'ignore' which completely ignores
                all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download'
                which downloads the attachment data to store locally. Default
                'reference'.
            parallel: Whether to retrieve messages in parallel. Default true.
                Currently parallelization is always on, since there is no
                reason to do otherwise.


        Returns:
            A list of Message objects.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        if not message_refs:
            return []

        if not parallel:
            return [
                self._build_message_from_ref(user_id, ref, attachments)
                for ref in message_refs
            ]

        max_num_threads = 12  # empirically chosen, prevents throttling
        target_msgs_per_thread = 10  # empirically chosen
        num_threads = min(
            math.ceil(len(message_refs) / target_msgs_per_thread), max_num_threads
        )
        batch_size = math.ceil(len(message_refs) / num_threads)
        message_lists: list[list[Message]] = [[] for _ in range(num_threads)]

        def thread_download_batch(thread_num: int) -> None:
            gmail = Gmail(_creds=self.creds)

            start = thread_num * batch_size
            end = min(len(message_refs), (thread_num + 1) * batch_size)
            message_lists[thread_num] = [
                gmail._build_message_from_ref(user_id, message_refs[i], attachments)
                for i in range(start, end)
            ]

            gmail.service.close()

        threads = [
            threading.Thread(target=thread_download_batch, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        return sum(message_lists, [])

    def _build_draft_from_ref(
        self, user_id: str, draft_ref: dict, attachments: str = "reference"
    ) -> Draft:
        """
        Creates a Draft object from a reference.

        Args:
            user_id: The username of the account the draft belongs to.
            draft_ref: The draft reference object returned from the Gmail
                API.
            attachments: Accepted values are 'ignore' which completely ignores
                all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download' which
                downloads the attachment data to store locally. Default
                'reference'.

        Returns:
            The Draft object.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """
        try:
            # Get draft JSON
            draft = (
                self.service.users()
                .drafts()
                .get(userId=user_id, id=draft_ref["id"])
                .execute()
            )
        except HttpError as error:
            # Pass along the error
            raise error

        else:
            id = draft["id"]
            message = self._build_message_from_ref(
                user_id, draft["message"], attachments
            )
            return Draft(user_id=user_id, id=id, message=message)

    def _ready_message_with_attachment(
        self, msg: MIMEMultipart, attachment: str
    ) -> None:
        """
        Converts attachment filepath to MIME objects and adds them to msg.

        Args:
            msg: The message to add attachments to.
            attachment: A attachment file path.

        """

        content_type, encoding = mimetypes.guess_type(attachment)

        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)
        with open(attachment, "rb") as file:
            raw_data = file.read()

            attm: MIMEBase
            if main_type == "text":
                attm = MIMEText(raw_data.decode("UTF-8"), _subtype=sub_type)
            elif main_type == "image":
                attm = MIMEImage(raw_data, _subtype=sub_type)
            elif main_type == "audio":
                attm = MIMEAudio(raw_data, _subtype=sub_type)
            elif main_type == "application":
                attm = MIMEApplication(raw_data, _subtype=sub_type)
            else:
                attm = MIMEBase(main_type, sub_type)
                attm.set_payload(raw_data)

        fname = os.path.basename(attachment)
        attm.add_header("Content-Disposition", "attachment", filename=fname)
        msg.attach(attm)

    def _ready_message_with_attachment_metadatum(
        self, msg: MIMEMultipart, attachment_metadatum: AttachmentMetadata
    ) -> None:
        """
        Converts attachment metadatum to MIME objects and adds them to msg.

        Args:
            msg: The message to add attachments to.
            attachment_metadatum: A attachment metadatum.

        """

        content_type = attachment_metadatum.content_type

        main_type, sub_type = content_type.split("/", 1)
        raw_data = attachment_metadatum.raw_data

        attm: MIMEBase
        if main_type == "text":
            attm = MIMEText(raw_data.decode("UTF-8"), _subtype=sub_type)
        elif main_type == "image":
            attm = MIMEImage(raw_data, _subtype=sub_type)
        elif main_type == "audio":
            attm = MIMEAudio(raw_data, _subtype=sub_type)
        elif main_type == "application":
            attm = MIMEApplication(raw_data, _subtype=sub_type)
        else:
            attm = MIMEBase(main_type, sub_type)
            attm.set_payload(raw_data)

        attm.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_metadatum.file_name,
        )
        msg.attach(attm)

    def _create_message(
        self,
        sender: str,
        to: str,
        subject: str = "",
        msg_html: str | None = None,
        msg_plain: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        references: list[str] | None = None,
        in_reply_to: str | None = None,
        attachments: list[str | AttachmentMetadata] | None = None,
        signature: bool = False,
        thread_id: str | None = None,
        user_id: str = "me",
    ) -> dict:
        msg = MIMEMultipart("mixed" if attachments else "alternative")
        msg["To"] = to
        msg["From"] = sender
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)

        if bcc:
            msg["Bcc"] = ", ".join(bcc)

        if references:
            msg["References"] = " ".join(references)

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to

        if signature:
            m = re.match(r".+\s<(?P<addr>.+@.+\..+)>", sender)
            address = m.group("addr") if m else sender
            account_sig = self._get_alias_info(address, user_id)["signature"]

            if msg_html is None:
                msg_html = ""

            msg_html += "<br /><br />" + account_sig

        attach_plain = MIMEMultipart("alternative") if attachments else msg
        attach_html = MIMEMultipart("related") if attachments else msg

        if msg_plain:
            attach_plain.attach(MIMEText(msg_plain, "plain"))

        if msg_html:
            attach_html.attach(MIMEText(msg_html, "html"))

        if attachments:
            attach_plain.attach(attach_html)
            msg.attach(attach_plain)
            for attachment in attachments:
                if isinstance(attachment, str):
                    self._ready_message_with_attachment(msg, attachment)
                elif isinstance(attachment, AttachmentMetadata):
                    self._ready_message_with_attachment_metadatum(msg, attachment)
        response = {"raw": base64.urlsafe_b64encode(msg.as_string().encode()).decode()}

        if thread_id:
            response["threadId"] = thread_id

        return response

    def _build_message_from_ref(
        self, user_id: str, message_ref: dict, attachments: str = "reference"
    ) -> Message:
        """
        Creates a Message object from a reference.

        Args:
            user_id: The username of the account the message belongs to.
            message_ref: The message reference object returned from the Gmail
                API.
            attachments: Accepted values are 'ignore' which completely ignores
                all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download' which
                downloads the attachment data to store locally. Default
                'reference'.

        Returns:
            The Message object.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        try:
            # Get message JSON
            message = (
                self.service.users()
                .messages()
                .get(userId=user_id, id=message_ref["id"])
                .execute()
            )

        except HttpError as error:
            # Pass along the error
            raise error

        else:
            msg_id = message["id"]
            thread_id = message["threadId"]
            label_ids = []
            if "labelIds" in message:
                user_labels = {x.id: x for x in self.list_labels(user_id=user_id)}
                label_ids = [user_labels[x] for x in message["labelIds"]]
            snippet = html.unescape(message["snippet"])

            payload = message["payload"]
            headers = payload["headers"]

            # Get header fields (date, from, to, subject)
            date = ""
            sender = ""
            recipient = ""
            subject = ""
            msg_hdrs = {}
            cc = []
            bcc = []
            for hdr in headers:
                if hdr["name"].lower() == "date":
                    try:
                        date = str(parser.parse(hdr["value"]).astimezone())
                    except Exception:
                        date = hdr["value"]
                elif hdr["name"].lower() == "from":
                    sender = hdr["value"]
                elif hdr["name"].lower() == "to":
                    recipient = hdr["value"]
                elif hdr["name"].lower() == "subject":
                    subject = hdr["value"]
                elif hdr["name"].lower() == "cc":
                    cc = hdr["value"].split(", ")
                elif hdr["name"].lower() == "bcc":
                    bcc = hdr["value"].split(", ")

                msg_hdrs[hdr["name"]] = hdr["value"]

            parts = self._evaluate_message_payload(
                payload, user_id, message_ref["id"], attachments
            )

            plain_msg = None
            html_msg = None
            attms = []
            for part in parts:
                if part["part_type"] == "plain":
                    if plain_msg is None:
                        plain_msg = part["body"]
                    else:
                        plain_msg += "\n" + part["body"]
                elif part["part_type"] == "html":
                    if html_msg is None:
                        html_msg = part["body"]
                    else:
                        html_msg += "<br/>" + part["body"]
                elif part["part_type"] == "attachment":
                    attm = Attachment(
                        service=self.service,
                        user_id=user_id,
                        msg_id=msg_id,
                        id=part["attachment_id"],
                        filename=part["filename"],
                        filetype=part["filetype"],
                        data=part["data"],
                    )
                    attms.append(attm)
            return Message(
                service=self.service,
                creds=self.creds,
                user_id=user_id,
                id=msg_id,
                thread_id=thread_id,
                recipient=recipient,
                sender=sender,
                subject=subject,
                date=date,
                snippet=snippet,
                plain=plain_msg,
                html=html_msg,
                label_ids=[label.id for label in label_ids],
                attachments=attms,
                headers=msg_hdrs,
                cc=cc,
                bcc=bcc,
            )

    def send_message(
        self,
        sender: str,
        to: str,
        subject: str = "",
        msg_html: str | None = None,
        msg_plain: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        references: Optional[list[str]] = None,
        in_reply_to: Optional[str] = None,
        attachments: list[str | AttachmentMetadata] | None = None,
        signature: bool = False,
        thread_id: Optional[str] = None,
        user_id: str = "me",
    ) -> Message:
        """Sends an email

        Args:
            references: The list of Message-Ids to be referenced.
            in_reply_to: The Message-Id to be replied to.
            thread_id: The thread ID to add the reply to.
        """
        msg = self._create_message(
            sender,
            to,
            subject,
            msg_html,
            msg_plain,
            cc=cc,
            bcc=bcc,
            references=references,
            in_reply_to=in_reply_to,
            attachments=attachments,
            signature=signature,
            thread_id=thread_id,
            user_id=user_id,
        )
        try:
            req = self.service.users().messages().send(userId="me", body=msg)
            res = req.execute()
            return self._build_message_from_ref(user_id, res, "reference")

        except HttpError as error:
            # Pass along the error
            raise error

    def create_draft(
        self,
        sender: str,
        to: str,
        subject: str = "",
        msg_html: str | None = None,
        attachments: list[str | AttachmentMetadata] | None = None,
        msg_plain: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        references: list[str] | None = None,
        in_reply_to: str | None = None,
        signature: bool = False,
        thread_id: str | None = None,
        user_id: str = "me",
    ) -> Draft:
        """
        Creates a draft.
        Args:
            sender: The email address the draft is being sent from.
            to: The email address the draft is being sent to.
            subject: The subject line of the email.
            msg_html: The HTML message of the email.
            msg_plain: The plain text alternate message of the email. This is
                often displayed on slow or old browsers, or if the HTML message
                is not provided.
            cc: The list of email addresses to be cc'd.
            bcc: The list of email addresses to be bcc'd.
            references: The list of Message-Ids to be referenced.
            in_reply_to: The Message-Id to be replied to.
            attachments: The list of attachment file names.
            signature: Whether the account signature should be added to the
                draft.
            thread_id: The thread ID to add the reply to.
            user_id: The address of the sending account. 'me' for the
                default address associated with the account.
        Returns:
            The Draft object representing the created draft.
        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.
        """
        msg = {
            "message": self._create_message(
                sender,
                to,
                subject,
                msg_html,
                msg_plain,
                cc=cc,
                bcc=bcc,
                references=references,
                in_reply_to=in_reply_to,
                attachments=attachments,
                signature=signature,
                thread_id=thread_id,
                user_id=user_id,
            )
        }

        try:
            req = self.service.users().drafts().create(userId="me", body=msg)
            res = req.execute()
            return self._build_draft_from_ref(user_id, res, "reference")

        except HttpError as error:
            # Pass along the error
            raise error

    def get_threads(
        self,
        user_id: str = "me",
        labels: Optional[list[Label]] = None,
        query: str = "",
        attachments: str = "reference",
        include_spam_trash: bool = False,
    ) -> list[Thread]:
        """
        Gets threads from your account.
        Args:
            user_id: the user's email address. Default 'me', the authenticated
                user.
            labels: label IDs threads must match.
            query: a Gmail query to match.
            attachments: accepted values are 'ignore' which completely
                ignores all attachments, 'reference' which includes attachment
                information but does not download the data, and 'download' which
                downloads the attachment data to store locally. Default
                'reference'.
            include_spam_trash: whether to include threads from spam or trash.
        Returns:
            A list of thread objects.
        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.
        """

        if labels is None:
            labels = []

        label_ids = [label.id for label in labels]

        try:
            response = (
                self.service.users()
                .threads()
                .list(
                    userId=user_id,
                    q=query,
                    labelIds=label_ids,
                    includeSpamTrash=include_spam_trash,
                )
                .execute()
            )

            thread_refs = []
            if "threads" in response:  # ensure request was successful
                thread_refs.extend(response["threads"])

            while "nextPageToken" in response:
                page_token = response["nextPageToken"]
                response = (
                    self.service.users()
                    .threads()
                    .list(
                        userId=user_id,
                        q=query,
                        labelIds=label_ids,
                        includeSpamTrash=include_spam_trash,
                        pageToken=page_token,
                    )
                    .execute()
                )

                thread_refs.extend(response["threads"])

            return self._get_threads_from_refs(user_id, thread_refs, attachments)

        except HttpError as error:
            # Pass along the error
            raise error
