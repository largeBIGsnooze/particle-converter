import os
import sys
from subprocess import run, DEVNULL
from src.logger import Logger

class TextureProcessor:

    def __init__(self, textures_path: str, is_texconv_present: bool):
        self.textures_path = textures_path
        self.out_textures_path = os.path.join(os.path.dirname(sys.executable), "out", "textures")
        self.args = [
            "texconv.exe",
            "-f",
            "BC7_UNORM",
            "-y",
            "-pow2",
            "-o",
            self.out_textures_path,
        ]
        self.is_texconv_present = is_texconv_present

    def convert(self, texture: str) -> None:
        if not texture or not self.is_texconv_present:
            return

        if not os.path.exists(self.textures_path):
            Logger.warn(f"Invalid textures_path: '{self.textures_path}', check your config.json")

        texture_name = texture.lower()

        if not os.path.splitext(texture_name)[1]:
            for texture in os.listdir(self.textures_path):
                if texture.lower().startswith(texture_name):
                    texture_name = texture

        output_file, ext = os.path.splitext(texture_name)

        input_path = os.path.join(self.textures_path, texture_name)
        output_file += ".DDS" if ext.isupper() else ".dds"
        output_path = os.path.join(self.out_textures_path, output_file)

        if not os.path.exists(input_path) or os.path.exists(output_path):
            return

        Logger.info(f"Converting texture: {texture_name}")
        run(
            [*self.args, input_path],
            stdin=DEVNULL,
            stdout=DEVNULL,
        )
