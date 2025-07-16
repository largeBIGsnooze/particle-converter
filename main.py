import json
import math
import io
import sys
import os
from typing import Dict, Any, Optional, Union
from dataclasses import is_dataclass
from enum import Enum
from src import classes as c


class ParticleException(Exception):
    def __init__(self, message):
        super().__init__(f"Failed to parse.\n{message}")


class SinsParticleFormatException(ParticleException):
    def __init__(self, prop: str, line_number: int):
        super().__init__(f'Expected "{prop}" in line: {line_number}\n')
        self.prop = prop
        self.line_number = line_number


class SinsParticleException(ParticleException):
    def __init__(self, message):
        super().__init__(message)


class SinsParticle:
    def __init__(self, particle_path: str) -> None:
        self.f: Optional[Union[io.TextIOWrapper, io.BufferedReader]] = None
        self.pos: int = 0
        self.line_number: int = 0

        self.curr_line: str = ""
        self.collector: dict = {}
        self.depth: int = 0

        self.particle_path: str = particle_path
        self.file: Optional[Union[c.TextureAnimation, c.ParticleEffect]] = None

        self.modifiers: list = []
        self.nodes: list = []
        self.emitters: list = []
        self.modifier_to_emitter_attachments: list = []
        self.emitter_to_node_attachments: list = []
        self.fade_values: dict = {}

    def _depth(self, curr_line: str) -> int:
        self.depth = (len(curr_line.replace("\t", "    ")) - len(curr_line.lstrip())) // 4
        return self.depth

    def _parse_object(self, depth: int, collector: dict) -> None:
        self.curr_line = self._next()

        while self.curr_line and self._curr_depth() == depth:
            key, value = self._curr_line_items()

            if self.line_number == 5:
                self._expect(self.curr_line, "NumEmitters")

            if key in ("EmitterType", "AffectorType"):
                emitter = {}
                map_types = {
                    "EmitterType": ("Emitters", "EmitterContents"),
                    "AffectorType": ("Affectors", "AffectorContents"),
                }
                array, contents = map_types[key]
                collector.setdefault(array, []).append(
                    {
                        key: value,
                        contents: emitter,
                    }
                )
                self.curr_line = self._next()
                self._expect(self.curr_line, contents)
                self._parse_emitter(emitter, depth + 1)
                continue

            collector[key] = value
            self.curr_line = self._next()

        self._build_particle_effect()

    def _build_particle_effect(self) -> None:
        self.emitter_to_node_attachments = [
            self.__serialize__(c.Attacher(i, i))
            for i in range(int(self.collector["ParticleSimulation"]["NumEmitters"]))
        ]
        self._build_modifier_to_emitter_attachments()
        self._build_emitters()
        self.modifiers = self._delete_fade_affectors()

        self.file = c.ParticleEffect(
            nodes=self.nodes,
            emitters=self.emitters,
            modifiers=self.modifiers,
            emitter_to_node_attachments=self.emitter_to_node_attachments,
            modifier_to_emitter_attachments=self.modifier_to_emitter_attachments,
        )

    def parse(self) -> "SinsParticle":
        try:
            if not os.path.exists(self.particle_path):
                raise FileNotFoundError(self.particle_path)

            self.f = open(self.particle_path, "rb")

            if int.from_bytes(self.f.read(3), byteorder="big") == 0x42494E:
                self.f.close()
                raise SinsParticleException(
                    "Convert it to TXT format before running this program."
                )

            self.f = open(self.particle_path, "r", encoding="utf-8")

            self.f.seek(0)
            self.pos = self.f.tell()

            magic = self._next()
            if "TXT" not in magic:
                self._expect(self.curr_line, "TXT")

            game_version = self.f.readline()
            if "sinsarchiveversion" not in game_version.lower():
                self.f.seek(self.pos)

            if self.particle_path.endswith(".texanim"):
                texanim = c.Texanim()
                for i in range(6):
                    self._next()
                    key, value = self._curr_line_items()
                    if not isinstance(value, list) and value.isdigit():
                        value = int(value)
                    texanim[key] = value
                self.file = texanim.to_texture_animation()
            elif self.particle_path.endswith(".particle"):
                simulation_start = self._next()

                self._expect(simulation_start, "ParticleSimulation")
                self.collector.setdefault(simulation_start, {})
                self.collector[simulation_start].setdefault("Emitters", [])
                self.collector[simulation_start].setdefault("Affectors", [])
                self._parse_object(1, self.collector[simulation_start])
        except FileNotFoundError as a:
            print(f"Failed to open '{a}'")
        except SinsParticleException as b:
            print(b)
        except Exception as f:
            print(f"Failed to parse: {f}")
        return self

    def __serialize__(self, obj: Any) -> Any:
        if hasattr(obj, "__serialize__"):
            return obj.__serialize__()
        elif isinstance(obj, Enum):
            return obj.name.lower()
        elif isinstance(obj, list):
            return [self.__serialize__(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: self.__serialize__(v) for k, v in obj.items()}
        elif is_dataclass(obj):
            result = {}
            for field in obj.__dataclass_fields__.values():
                value = getattr(obj, field.name)
                if value is not None:
                    result[field.name] = self.__serialize__(value)
            return result
        else:
            return obj

    def _build_node_attachment(self, emitter_id: int, emitter: Any) -> None:
        x, y, z = emitter["Position"]

        rot_pitch, rot_yaw, rot_roll = map(
            lambda b: -math.radians(b),
            (
                emitter["RotateAboutForward"],
                emitter["RotateAboutUp"],
                emitter["RotateAboutCross"],
            ),
        )

        node = c.Node(
            emitter_id,
            emitter["Name"],
            c.Vector2f(x, x),
            c.Vector2f(y, y),
            c.Vector2f(z, z),
            c.Vector2f(rot_yaw, rot_yaw),
            c.Vector2f(rot_pitch, rot_pitch),
            c.Vector2f(rot_roll, rot_roll),
        )
        self.nodes.append(self.__serialize__(node))

    def _build_emitters(self) -> None:
        particle_simulation = self.collector["ParticleSimulation"]

        for emitter_id, _emitter in enumerate(particle_simulation["Emitters"]):
            emitter = _emitter["EmitterContents"]

            self._build_node_attachment(emitter_id, emitter)

            facing_type = c.FacingType.parse(emitter["ParticleFacing"])

            root = c.Emitter(
                id=emitter_id,
                type=c.EmitterType.parse(_emitter["EmitterType"].upper()),
                name=emitter["Name"],
                emit_rate=c.EmitRate(),
                particle=c.Particle(
                    mesh=c.Mesh(),
                    billboard=c.Billboard(
                        uber_constants=c.UberConstants(basic_constants=c.BasicConstants())
                    ),
                ),
            )

            if facing_type != c.FacingType.FACE_CAMERA:
                root.particle.billboard.facing_type = facing_type.name.lower()

            root.emit_rate.primary_emit_rate = c.Vector2f(*[emitter["EmitRate"]] * 2)

            if not emitter["HasInfiniteEmitCount"]:
                root.emit_max_particle_count = c.Vector2f(*[emitter["MaxEmitCount"]] * 2)

            root.particle.billboard.width = c.Vector2f(*[emitter["ParticleWidth"]] * 2)
            root.particle.billboard.height = c.Vector2f(*[emitter["ParticleHeight"]] * 2)

            anchor = c.Anchor.parse(emitter["BillboardAnchor"])

            if anchor != c.Anchor.CENTER:
                root.particle.billboard.anchor = anchor.name.lower()

            root.particle.max_duration = c.Vector2f(*[emitter["ParticleLifeTime"]] * 2)

            if emitter["TotalLifeTime"] > 0:
                root.emit_duration = c.Vector2f(*[emitter["TotalLifeTime"]] * 2)

            root.particle.color = emitter["ParticleStartColor"]

            root.emit_start_delay = c.Vector2f(*[emitter["StartTime"]] * 2)
            root.particle.mass = c.Vector2f(*[emitter["ParticleStartMass"]] * 2)

            if emitter["MeshName"]:
                root.particle.type = "mesh"
                root.particle.mesh.shader = c.MeshShader.SHIP
                root.particle.mesh.mesh = emitter["MeshName"]
            else:
                root.particle.type = "billboard"

            root.is_visible = emitter["Enabled"]

            if root.name in self.fade_values:
                fade = self.fade_values[root.name]
                root.particle.fade_in_time = c.Vector2f(
                    *[fade["fade_in_time"] if fade["fade_in_enabled"] else 0.0] * 2
                )
                root.particle.fade_out_time = c.Vector2f(
                    *[fade["fade_out_time"] if fade["fade_out_enabled"] else 0.0] * 2
                )

            if "AngleVariance" in emitter:
                root.angle_variance = c.Vector2f(
                    emitter["AngleVariance"], emitter["AngleVariance"]
                )

            root.particle.billboard.rotation = c.Vector2f(
                emitter["ParticleMinStartRotation"],
                emitter["ParticleMaxStartRotation"],
            )
            root.particle.billboard.rotation_speed = c.Vector2f(
                emitter["ParticleMinStartAngularSpeed"],
                emitter["ParticleMaxStartAngularSpeed"],
            )

            rotation_type = c.RotationType.parse(emitter["RotationDirectionType"])
            if rotation_type == c.RotationType.RANDOM:
                root.particle.billboard.rotation_speed.min = -abs(
                    root.particle.billboard.rotation_speed.min
                )
            elif rotation_type == c.RotationType.COUNTER_CLOCKWISE:
                root.particle.billboard.rotation_speed.max = -abs(
                    root.particle.billboard.rotation_speed.max
                )
            elif rotation_type == c.RotationType.CLOCKWISE:
                root.particle.billboard.rotation_speed.max = abs(
                    root.particle.billboard.rotation_speed.max
                )

            if root.type == c.EmitterType.POINT:
                root.forward_velocity = c.Vector2f(
                    emitter["ParticleMinStartLinearSpeed"],
                    emitter["ParticleMaxStartLinearSpeed"],
                )

            for i, texture in enumerate(emitter["Textures"]):
                root.particle.billboard[f"texture_{i}"] = texture

            root.particle.billboard.texture_animation = emitter["textureAnimationName"]
            root.particle.billboard.texture_animation_fps = c.Vector2f(
                *[emitter["textureAnimationOnParticleFPS"]] * 2
            )

            if root.type == c.EmitterType.RING:

                root.radius_x = c.Vector2f(
                    emitter["RingRadiusXMin"], emitter["RingRadiusXMax"]
                )
                root.radius_y = c.Vector2f(
                    emitter["RingRadiusYMin"], emitter["RingRadiusYMax"]
                )
                root.angle_range = c.Vector2f(
                    emitter["SpawnAngleStart"], emitter["SpawnAngleStop"]
                )

                root.tangential_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedTangential"]] * 2
                )

                root.use_edge = False
                root.normal_offset = c.Vector2f(0, 0)
                root.normal_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedRingNormal"]] * 2
                )
                root.radial_velocity = c.Vector2f(0, 0)
                root.angle_range_behavior = c.AngleRangeBehavior.RANDOM

            if root.type == c.EmitterType.SPHERE:
                for key in ("X", "Y", "Z"):
                    root[f"radius_{key.lower()}"] = c.Vector2f(
                        emitter[f"SphereRadius{key}Min"],
                        emitter[f"SphereRadius{key}Max"],
                    )

                root.azimuthal_tangential_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedAzimuthalTangential"]] * 2
                )

                root.polar_tangential_velocity = c.Vector2f(
                    emitter["ParticleMaxStartSpeedPolarTangential"],
                    emitter["ParticleMaxStartSpeedPolarTangential"],
                )
                root.latitude_angle_range = c.Vector2f(
                    emitter["SpawnAngleLatitudinalStart"],
                    emitter["SpawnAngleLatitudinalStop"],
                )
                root.longitude_angle_range = c.Vector2f(
                    emitter["SpawnAngleLongitudinalStart"],
                    emitter["SpawnAngleLongitudinalStop"],
                )

                root.radial_velocity = c.Vector2f(1, 2)
                root.use_surface = False

            self.emitters.append(self.__serialize__(root))

        for modifier_id, _modifier in enumerate(particle_simulation["Affectors"]):
            modifier = _modifier["AffectorContents"]
            affector_type = _modifier["AffectorType"]

            root = c.Modifier(
                id=modifier_id,
                name=modifier["Name"] or affector_type,
                type=c.ModifierType.parse(
                    SinsParticle._normalize_affector_type(affector_type).upper()
                ),
            )

            if root.type == c.ModifierType.ROTATE_ABOUT_AXIS:
                root.type = c.ModifierType.ROTATE
                root.axis_of_rotation = c.Vector3f(*modifier["AxisOfRotation"])
                root.axis_origin = c.Vector3f(*modifier["AxisOrigin"])
                root.radius = modifier["Radius"]
                root.angular_velocity = c.Vector2f(*[modifier["AngularVelocity"]] * 2)
            if root.type == c.ModifierType.KILL:
                root.point = c.Vector3f(*modifier["Point"])
                root.op = c.Op.NEAR_POINT
                root.tolerance = c.Vector2f(*[modifier["Distance"]] * 2)
            if root.type == c.ModifierType.COLOR:
                root.begin_color = modifier["StartColor"]
                root.end_color = modifier["EndColor"]
                root.change_duration = c.Vector2f(*[modifier["TransitionPeriod"]] * 2)
                root.change_duration_context = "particle_time_elapsed"
            if root.type == c.ModifierType.SIZE_OSCILLATOR:
                pass
            if root.type == c.ModifierType.LINEAR_FORCE_IN_DIRECTION:
                root.type = c.ModifierType.PUSH
                root.direction = c.Vector3f(*modifier["Direction"])
                root.force = c.ModifierForce()
                root.force.range = c.Vector2f(modifier["MinForce"], modifier["MaxForce"])
            if root.type == c.ModifierType.JITTER:
                root.force = c.ModifierForce()
                root.force.type = c.ForceType.RANDOM
                root.force.range = c.Vector2f(*[modifier["JitterForce"]] * 2)
                root.op = c.Op.RANDOM_JITTER
                if modifier["UseCommonForce"]:
                    root.is_random_jitter_shared = modifier["UseCommonForce"]
            if root.type == c.ModifierType.PUSH:
                root.force = c.ModifierForce()
                root.force.type = c.ForceType.CONSTANT
                root.force.range = c.Vector2f(
                    modifier["MinForce"] / 25, modifier["MaxForce"] / 25
                )
                root.op = c.Op.TO_POINT_IN_EMITTER_SPACE
            if root.type == c.ModifierType.SIZE:
                root.width_change_rate = c.Vector2f(*[modifier["WidthInflateRate"]] * 2)
                root.height_change_rate = c.Vector2f(*[modifier["HeightInflateRate"]] * 2)
            # else:
            root.start_delay = c.Vector2f(*[modifier["StartTime"]] * 2)

            if not modifier["HasInfiniteLifeTime"]:
                root.particle_time_duration = c.Vector2f(*[modifier["TotalLifeTime"]] * 2)
                print(root.particle_time_duration)

            self.modifiers.append(self.__serialize__(root))

    def _build_modifier_to_emitter_attachments(self) -> None:

        for attacher_id, affector in enumerate(
            self.collector["ParticleSimulation"]["Affectors"]
        ):
            contents = affector["AffectorContents"]

            if "AttachedEmitters" in contents:
                is_fade_affector = affector["AffectorType"].lower() == "fade"
                for attached in contents["AttachedEmitters"]:
                    if is_fade_affector:
                        self.fade_values[attached] = {
                            "fade_in_enabled": contents["DoFadeIn"],
                            "fade_out_enabled": contents["DoFadeOut"],
                            "fade_in_time": contents["FadeInTime"],
                            "fade_out_time": contents["FadeOutTime"],
                        }
                    for attachee_id, emitter in enumerate(
                        self.collector["ParticleSimulation"]["Emitters"]
                    ):
                        if (
                            emitter["EmitterContents"]["Name"] == attached
                            and not is_fade_affector
                        ):
                            self.modifier_to_emitter_attachments.append(
                                self.__serialize__(c.Attacher(attacher_id, attachee_id))
                            )

    def _next_line(self) -> str:
        self.pos = self.f.tell()
        next_line = self.f.readline()
        self.f.seek(self.pos)
        return next_line

    @staticmethod
    def _convert_value(value: Any) -> Any:
        if value.startswith('"') and value.endswith('"'):
            value = str(value).strip('"')
        elif value.startswith("[") and value.endswith("]"):
            value = value.strip("[]").split()
            if any("," in _ for _ in value):
                value = " ".join(value).replace(",", "").split()
                value = list(
                    map(
                        lambda x: int(float(x)) if float(x).is_integer() else float(x),
                        value,
                    )
                )
            else:
                value = list(map(float, value))
        elif "." in value:
            value = float(value.strip('"'))
        elif value in ("TRUE", "FALSE"):
            value = eval(f"{value[0].upper()}{value[1:].lower()}")

        return value

    @staticmethod
    def _normalize_texture_name(texture_name: str) -> str:
        return os.path.basename(
            texture_name.strip('"').lower().replace(".tga", "").replace(".dds", "")
        )

    def _parse_emitter(self, emitter: Dict[str, Any], depth: int) -> None:
        self.curr_line = self._next()
        while self.curr_line:
            curr_depth = self._curr_depth()
            next_depth = self._depth(self._next_line())

            if next_depth == 3:
                self._expect(self.curr_line, "Orientation")
                key = self.curr_line.strip()
                self.curr_line = self._next()
                for _ in range(self._curr_depth()):
                    vec3 = self.curr_line.strip().strip("[]").split()
                    emitter.setdefault(key, []).append(list(map(float, vec3)))
                    self.curr_line = self._next()
                continue
            elif curr_depth < depth:
                break

            key, value = self._curr_line_items()

            if "numTextures" in self.curr_line:
                emitter.setdefault("Textures", [])
                for _ in range(int(value)):
                    self.curr_line = self._next()
                    texture_name = SinsParticle._normalize_texture_name(
                        self._curr_line_items()[1]
                    )
                    if texture_name != "":
                        texture_name += "_clr"
                    emitter["Textures"].append(texture_name)

            if "numAttachedEmitters" in self.curr_line and int(value) != 0:
                emitter.setdefault("AttachedEmitters", [])
                for _ in range(int(str(value))):
                    self.curr_line = self._next()
                    attached_name = self._curr_line_items()[1].strip('"')

                    emitter["AttachedEmitters"].append(attached_name)

            emitter[key] = value
            if "textureAnimationName" in self.curr_line and value:
                emitter["textureAnimationName"] = (
                    f"{value.lower().split('.')[0]}.texture_animation"
                )

            self.curr_line = self._next()

    def _curr_depth(self) -> int:
        self.depth = self._depth(self.curr_line)
        return self.depth

    def _curr_line_items(self) -> list:
        return list(map(self._convert_value, self.curr_line.strip().split(None, 1)))

    @staticmethod
    def _normalize_affector_type(affector_type: str) -> str:
        return {
            "LinearForceToPoint": "push",
            "Jitter": "jitter",
            "LinearInflate": "size",
            "SizeOscillator": "size_oscillator",
            "Fade": "fade",
            "ColorOscillator": "color",
            "LinearForceInDirection": "linear_force_in_direction",
            "RotateAboutAxis": "rotate_about_axis",
            "KillParticlesNearPoint": "kill",
        }.get(affector_type, affector_type)

    def _delete_fade_affectors(self) -> list:
        return list(filter(lambda x: x["type"] != "fade", self.modifiers))

    def _expect(self, line: str, expected: str) -> None:
        if expected not in line:
            raise SinsParticleFormatException(expected, self.line_number)

    def _next(self, step: int = 1) -> str:
        for _ in range(step):
            self.curr_line = self.f.readline().rstrip("\n")
            self.pos = self.f.tell()
            self.line_number += 1
        return self.curr_line

    def save(self, save_path: str = "./examples/output/test.particle_effect") -> None:
        if self.file:
            with open(save_path, "w") as f:
                json.dump(self.__serialize__(self.file), f, indent=2)


if __name__ == "__main__":
    try:
        exe_path = os.path.dirname(sys.executable)
        out_path = os.path.join(exe_path, "out")
        if len(sys.argv) < 2:
            print("Drop a Sins 1 .particle file\n")
            os.system("pause")
            sys.exit(1)

        os.makedirs(out_path, exist_ok=True)

        for file in sys.argv[1:]:
            file_name = os.path.basename(file)
            name = f"{file_name.split('.')[0]}"

            if file.endswith(".particle"):
                target_path = os.path.join(out_path, "effects")
                extension = ".particle_effect"
                print(f"{file_name} -> {name + extension}")
            elif file.endswith(".texanim"):
                target_path = os.path.join(out_path, "texture_animations")
                extension = ".texture_animation"
                print(f"{file_name} -> {name + extension}")
            else:
                print(f"Skipping: {name}")
                continue
            os.makedirs(target_path, exist_ok=True)
            parser = SinsParticle(particle_path=file).parse()
            parser.save(os.path.join(target_path, name + extension))

        os.system("pause")
    except Exception as e:
        input(str(e))
