"""
Read unread inbox and responds to questions.
"""

import os
import time

from miramail import MiraMail
from miramail.gmail import Gmail

os.environ["OPENAI_API_KEY"] = ""

gmail = Gmail(credentials_file="dev_credentials.json", token_file="dev_token.json")
mail = MiraMail(client=gmail)
while True:
    print("Checking for new messages...")
    mail.respond()
    time.sleep(10)
