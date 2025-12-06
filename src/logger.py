from colorama import Fore
from typing import Any


class Logger:
    @staticmethod
    def print(message: str, color: Any = Fore.WHITE) -> None:
        print(color + f"{message}")

    @staticmethod
    def info(message: str, color: Any = Fore.CYAN) -> None:
        Logger.print(f"[INFO]: {message}", color)

    @staticmethod
    def warn(message: str, color: Any = Fore.YELLOW) -> None:
        Logger.print(f"[WARN]: {message}", color)

    @staticmethod
    def error(message: str, color: Any = Fore.RED) -> None:
        Logger.print(f"[ERROR]: {message}", color)
