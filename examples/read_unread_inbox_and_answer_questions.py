"""
Read unread inbox and responds to questions.
"""

import os
import time

from mirascope.openai import OpenAICall, OpenAICallParams

from miramail import MiraMail
from miramail.gmail import Gmail

os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"


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


def handle_body(body: list[str]) -> str:
    return Reply(body=body).call().content


gmail = Gmail(credentials_file="credentials.json", token_file="token.json")
mail = MiraMail(client=gmail)
while True:
    print("Checking for new messages...")
    mail.respond(handle_body=handle_body)
    time.sleep(10)
