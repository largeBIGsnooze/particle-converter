from colorama import Fore


class ParticleException(Exception):
    def __init__(self, message: str):
        super().__init__(Fore.RED + f"Failed to parse.\n{message}")


class SinsParticleFormatException(ParticleException):
    def __init__(self, prop: str, line_number: int):
        super().__init__(f'Expected "{prop}" in line: {line_number}\n')
        self.prop = prop
        self.line_number = line_number


class SinsParticleException(ParticleException):
    def __init__(self, message: str):
        super().__init__(message)
