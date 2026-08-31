import re
from dataclasses import dataclass

# NOTE: may not work when game is set to language with a different alphabet
PLAYER_MESSAGE_REGEX = re.compile(
    r"\[(CT|T|ALL)\]\s+(?=([^\u200E\uFE6B]+))\2[^:]*:\s(.+)"
)

@dataclass
class ChatMessage:
    chat: str
    player: str
    text: str

def parse_message(text: str) -> ChatMessage | None:
    if len(text) < 16:
        return None

    # strip date and time
    text = text[15:].strip()

    # attempt to match with regex
    match = PLAYER_MESSAGE_REGEX.search(text)
    if not match:
        return None

    chat, player, text = match.groups()
    return ChatMessage(chat, player, text)
