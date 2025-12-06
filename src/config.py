import os
import json
from json import JSONDecodeError
from typing import Any, Optional


class Config:
    def __init__(self, exe_path: str):
        self.exe_path = exe_path
        self.config_path = os.path.join(exe_path, "config.json")

    def create(self, bypass: bool = False) -> "Config":
        if not os.path.exists(self.config_path) and not bypass:
            with open(self.config_path, "w") as f:
                json.dump({"textures_path": ""}, f, indent=2)
        return self

    def read(self) -> Any:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)["textures_path"]
        except:
            self.create(True)
