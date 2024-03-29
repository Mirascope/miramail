# --------------------------------------------------------------------------------
# Source: https://github.com/jeremyephron/simplegmail/pull/90/files
# By: linkyndy
#
# This code is used in accordance with the repository's license, and this reference
# serves as an acknowledgment of the original author's contribution to this project.
#
# Note that the code below is modified slightly from the original source.
# --------------------------------------------------------------------------------

from pydantic import BaseModel, Field

from .message import Message


class Draft(BaseModel):
    """
    The Draft class for drafts in your Gmail mailbox. This class should not
    be manually constructed. Contains all information about the associated
    draft.

    """

    user_id: str = Field(
        default_factory=str,
        description="The username of the account the message belongs to.",
    )
    id: str = Field(
        default_factory=str,
        description="The draft id.",
    )
    message: Message = Field(
        description="The message.",
    )

    def __repr__(self) -> str:
        """Represents the object by its sender, recipient, and id."""

        return f"Draft(to: {self.message.recipient}, from: {self.message.sender}, id: {self.id})"
