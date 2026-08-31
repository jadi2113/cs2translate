import json
import os.path
import logging as log
from dataclasses import asdict, dataclass
from tkinter import messagebox as mb

@dataclass
class Config:
    console_log_path: str = ""
    output_language: str = "en"
    ignore_own_messages: bool = False # disable, no username by default
    own_username: str = ""
    ignore_english: bool = True

    def save(self, path: str):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4, ensure_ascii=False)
        except (TypeError, OSError) as e:
            log.error("Unable to save config")
            mb.showerror(
                "Config Save Error",
                f"Settings could not be saved.\n{e!s}"
            )

    @staticmethod
    def load(path: str) -> "Config":
        if not os.path.exists(path):
            # initialize with default values
            return Config()

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.error("Unable to load config, resetting to defaults")
            mb.showerror(
                "Config Load Error",
                f"Settings could not be loaded, resetting to defaults.\n{e!s}"
            )
            return Config()

        # reset missing keys to defaults
        defaults = Config()
        return Config(**{
            **asdict(defaults),
            **{k: v for k, v in data.items() if k in asdict(defaults)}
        })
