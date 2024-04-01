# --------------------------------------------------------------------------------
# Source: https://github.com/jeremyephron/simplegmail
# By: jeremyephron
#
# This code is used in accordance with the repository's license, and this reference
# serves as an acknowledgment of the original author's contribution to this project.
#
# Note that the code below is modified from the original source.
# --------------------------------------------------------------------------------


from typing import Literal, Optional

from pydantic import BaseModel, Field


class Label(BaseModel):
    """
    A Gmail label object.

    This class should not typically be constructed directly but rather returned
    from Gmail.list_labels().

    Args:
        name: The name of the Label.
        id: The ID of the label.

    Attributes:
        name (str): The name of the Label.
        id (str): The ID of the label.

    """

    id: str = Field(description="The ID of the label.")
    name: str = Field(description="The name of the Label.")
    message_list_visibility: Optional[Literal["show", "hide"]] = Field(
        description="The visibility of messages with this label in the message list in \
                     the Gmail web interface.",
        default=None,
    )
    label_list_visibility: Optional[
        Literal["label_show", "label_hide", "label_show_if_unread"]
    ] = Field(
        description="The visibility of this label in the label list in the Gmail web \
                     interface.",
        default=None,
    )
    type: Optional[Literal["system", "user"]] = Field(
        description="The type of the label.", default=None
    )

    def __repr__(self) -> str:
        return f"Label(name={self.name!r}, id={self.id!r})"

    def __str__(self) -> str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            # Can be compared to a string of the label ID
            return self.id == other
        elif isinstance(other, Label):
            return self.id == other.id
        else:
            return False


INBOX = Label(id="INBOX", name="INBOX")
SPAM = Label(id="SPAM", name="SPAM")
TRASH = Label(id="TRASH", name="TRASH")
UNREAD = Label(id="UNREAD", name="UNREAD")
STARRED = Label(id="STARRED", name="STARRED")
SENT = Label(id="SENT", name="SENT")
IMPORTANT = Label(id="IMPORTANT", name="IMPORTANT")
DRAFT = Label(id="DRAFT", name="DRAFT")
PERSONAL = Label(id="CATEGORY_PERSONAL", name="CATEGORY_PERSONAL")
SOCIAL = Label(id="CATEGORY_SOCIAL", name="CATEGORY_SOCIAL")
PROMOTIONS = Label(id="CATEGORY_PROMOTIONS", name="CATEGORY_PROMOTIONS")
UPDATES = Label(id="CATEGORY_UPDATES", name="CATEGORY_UPDATES")
FORUMS = Label(id="CATEGORY_FORUMS", name="CATEGORY_FORUMS")
