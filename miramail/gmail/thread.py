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


class Thread(BaseModel):
    """
    The Thread class for threads in your Gmail mailbox. This class should not
    be manually constructed. Contains all information about the associated
    thread.
    """

    user_id: str = Field(
        default_factory=str,
        description="The username of the account the thread belongs to.",
    )
    id: str = Field(
        default_factory=str,
        description="The thread id.",
    )
    snippet: str = Field(
        default_factory=str,
        description="The snippet line for the thread.",
    )
    messages: list[Message] = Field(
        default_factory=list,
        description="A list of messages.",
    )

    def __repr__(self) -> str:
        """Represents the object by its id."""

        return f"Thread(id: {self.id})"
