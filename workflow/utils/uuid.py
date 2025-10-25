import random
import string

class UUIDGenerator:
    @staticmethod
    def generate(length: int = 8) -> str:
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))