# logger.py

import os
from datetime import datetime


class Logger:

    def __init__(self, file_name="logs.txt"):
        self.file_name = file_name

        # Create file if not exists
        if not os.path.exists(self.file_name):
            with open(self.file_name, "w") as f:
                pass

    def log(self, flag, message):
        """
        flag: string like INFO, ERROR, SUCCESS, WARNING
        message: log message string
        """

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        formatted = f"[{now}][{flag}] {message}\n"

        with open(self.file_name, "a", encoding="utf-8") as f:
            f.write(formatted)
