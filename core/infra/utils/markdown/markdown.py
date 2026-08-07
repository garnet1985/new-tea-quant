from typing import Any

class MarkdownWriter:

    tokens: dict[str, Any]
    file_path: str
    template_content: str

    def __init__(self, filename: str):
        self.filename = filename

    @classmethod
    def init(file_path: str) -> "MarkdownWriter":
        pass

    @classmethod
    def fill(self, token: str, content: str):
        self.tokens[token] = content

    @classmethod
    def save(self):
        pass

    @classmethod
    def clear(self):
        self.tokens = {}