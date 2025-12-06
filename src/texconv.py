from src.logger import Logger
import os
from colorama import Fore


class Texconv:
    def __init__(self, exe_path: str) -> None:
        self.exe_path = exe_path

    def exists(self) -> bool:
        if os.path.exists(os.path.join(self.exe_path, "texconv.exe")):
            Logger.info("texconv.exe detected. Texture conversion enabled.\n", Fore.GREEN)
            os.makedirs(os.path.join(self.exe_path, "out", "textures"), exist_ok=True)
            return True
        return False
