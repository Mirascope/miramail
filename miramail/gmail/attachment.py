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
import os
from typing import Optional

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from pydantic import BaseModel, ConfigDict


class Attachment(BaseModel):
    service: Resource
    user_id: str
    msg_id: str
    id: str
    filename: str
    filetype: str
    data: Optional[bytes] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def download(self) -> None:
        """
        Downloads the data for an attachment if it does not exist.

        Raises:
            googleapiclient.errors.HttpError: There was an error executing the
                HTTP request.

        """

        if self.data is not None:
            return
        try:
            # Get draft JSON
            res = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId=self.user_id, messageId=self.msg_id, id=self.id)
                .execute()
            )
        except HttpError as error:
            # Pass along the error
            raise error
        else:
            data = res["data"]
            self.data = base64.urlsafe_b64decode(data)

    def save(self, filepath: Optional[str] = None, overwrite: bool = False) -> None:
        """
        Saves the attachment. Downloads file data if not downloaded.

        Args:
            filepath: where to save the attachment. Default None, which uses
                the filename stored.
            overwrite: whether to overwrite existing files. Default False.

        Raises:
            FileExistsError: if the call would overwrite an existing file and
                overwrite is not set to True.

        """

        if filepath is None:
            filepath = self.filename

        if self.data is None:
            self.download()

        if not overwrite and os.path.exists(filepath):
            raise FileExistsError(
                f"Cannot overwrite file '{filepath}'. Use overwrite=True if "
                f"you would like to overwrite the file."
            )
        if self.data:
            with open(filepath, "wb") as f:
                f.write(self.data)
