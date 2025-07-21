import json
import math
import os
from typing import Dict, Any, Optional, Union, TextIO, cast
from dataclasses import is_dataclass
from enum import Enum
from src import classes as c
from colorama import Fore
import colorama
import sys


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


class SinsParticle:
    def __init__(self, particle_path: str) -> None:
        self.f: TextIO
        self.pos: int = 0
        self.line_number: int = 0

        self.curr_line: str = ""
        self.collector: dict[str, Any] = {}
        self.depth: int = 0

        self.particle_path: str = particle_path
        self.file: Optional[Union[c.TextureAnimation, c.ParticleEffect]] = None

        self.modifiers: list[c.Modifier] = []
        self.nodes: list[c.Node] = []
        self.emitters: list[c.Emitter] = []
        self.modifier_to_emitter_attachments: list[c.Attacher] = []
        self.emitter_to_node_attachments: list[c.Attacher] = []
        self.fade_values: dict[int, Any] = {}

    def _depth(self, curr_line: str) -> int:
        self.depth = (
            len(curr_line.replace("\t", "    ")) - len(curr_line.lstrip())
        ) // 4
        return self.depth

    def _parse_object(self, depth: int, collector: dict[str, Any]) -> None:
        self.curr_line = self._next()

        while self.curr_line and self._curr_depth() == depth:
            key, value = self._curr_line_items()

            if self.line_number == 5:
                self._expect(self.curr_line, "NumEmitters")

            if key in ("EmitterType", "AffectorType"):
                emitter: dict[str, Any] = {}
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
            c.Attacher(i, i)
            for i in range(int(self.collector["ParticleSimulation"]["NumEmitters"]))
        ]
        self._build_modifier_to_emitter_attachments()
        self._build_emitters()
        self.modifiers = self._delete_fade_affectors()

        self.file = self.__serialize__(
            c.ParticleEffect(
                nodes=self.nodes,
                emitters=self.emitters,
                modifiers=self.modifiers,
                emitter_to_node_attachments=self.emitter_to_node_attachments,
                modifier_to_emitter_attachments=self.modifier_to_emitter_attachments,
            )
        )

    def parse(self) -> "SinsParticle":
        try:
            with open(self.particle_path, "rb") as f:
                if int.from_bytes(f.read(3), byteorder="big") == 0x42494E:
                    raise SinsParticleException(
                        "Convert it to TXT format before running this program."
                    )

            with open(self.particle_path, "r", encoding="utf-8") as f:  # type: ignore
                self.f = cast(TextIO, f)
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
                        texanim[key] = value
                    self.file = texanim.to_texture_animation()
                elif self.particle_path.endswith(".particle"):
                    simulation_start = self._next()

                    self._expect(simulation_start, "ParticleSimulation")
                    self.collector.setdefault(simulation_start, {})
                    self.collector[simulation_start].setdefault("Emitters", [])
                    self.collector[simulation_start].setdefault("Affectors", [])
                    self._parse_object(1, self.collector[simulation_start])
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

        yaw, pitch, roll = list(
            map(
                lambda r: (r - 180) % 360 - 180,
                [
                    emitter["RotateAboutUp"],
                    emitter["RotateAboutForward"],
                    emitter["RotateAboutCross"],
                ],
            )
        )

        yaw = math.radians(yaw if yaw < 0 else -yaw)
        pitch = math.radians(-pitch)
        roll = math.radians(-roll)

        node = c.Node(
            emitter_id,
            emitter["Name"],
            c.Vector2f(x, x),
            c.Vector2f(y, y),
            c.Vector2f(z, z),
            c.Vector2f(yaw, yaw),
            c.Vector2f(pitch, pitch),
            c.Vector2f(roll, roll),
        )
        self.nodes.append(node)

    def _build_emitters(self) -> None:
        particle_simulation = self.collector["ParticleSimulation"]

        for emitter_id, _emitter in enumerate(particle_simulation["Emitters"]):
            emitter = _emitter["EmitterContents"]

            self._build_node_attachment(emitter_id, emitter)

            facing_type = c.FacingType.parse(emitter["ParticleFacing"])

            e_root: c.Emitter = c.Emitter(
                id=emitter_id,
                type=c.EmitterType.parse(_emitter["EmitterType"].upper()),
                name=emitter["Name"],
                emit_rate=c.EmitRate(),
                particle=c.Particle(
                    mesh=c.Mesh(),
                    billboard=c.Billboard(
                        uber_constants=c.UberConstants(
                            basic_constants=c.BasicConstants()
                        )
                    ),
                ),
            )

            if facing_type != c.FacingType.FACE_CAMERA:
                e_root.particle.billboard.facing_type = facing_type

            e_root.emit_rate.primary_emit_rate = c.Vector2f(*[emitter["EmitRate"]] * 2)

            if not emitter["HasInfiniteEmitCount"]:
                e_root.emit_max_particle_count = c.Vector2f(
                    *[emitter["MaxEmitCount"]] * 2
                )

            e_root.particle.billboard.width = c.Vector2f(
                *[emitter["ParticleWidth"]] * 2
            )
            e_root.particle.billboard.height = c.Vector2f(
                *[emitter["ParticleHeight"]] * 2
            )

            anchor = c.Anchor.parse(emitter["BillboardAnchor"])

            if anchor != c.Anchor.CENTER:
                e_root.particle.billboard.anchor = anchor.name.lower()

            e_root.particle.max_duration = c.Vector2f(
                *[emitter["ParticleLifeTime"]] * 2
            )

            if not emitter["HasInfiniteLifeTime"]:
                e_root.emit_duration = c.Vector2f(*[emitter["TotalLifeTime"]] * 2)
                if emitter["TotalLifeTime"] <= 0:
                    print(
                        Fore.YELLOW
                        + f"\tWarning: {e_root.name} 'TotalLifeTime' must be > 0 if 'HasInfiniteLifeTime' is FALSE"
                    )
                elif emitter["TotalLifeTime"] < 0.02:
                    print(
                        Fore.CYAN
                        + f"\tInfo: {e_root.name} 'TotalLifeTime' must be > 0.01 or it won't play. Defaulting to 1.0"
                    )
                    e_root.emit_duration = c.Vector2f(1.0, 1.0)

            e_root.particle.color = emitter["ParticleStartColor"]

            e_root.emit_start_delay = c.Vector2f(*[emitter["StartTime"]] * 2)
            e_root.particle.mass = c.Vector2f(*[emitter["ParticleStartMass"]] * 2)

            if emitter["MeshName"]:
                e_root.particle.type = "mesh"
                e_root.particle.mesh.shader = c.MeshShader.SHIP
                e_root.particle.mesh.mesh = emitter["MeshName"]
            else:
                e_root.particle.type = "billboard"

            e_root.is_visible = emitter["Enabled"]

            for _, fade_value in self.fade_values.items():
                if e_root.name in fade_value:
                    fade = self.fade_values[_][e_root.name]
                    if fade["do_fade_in"]:
                        e_root.particle.fade_in_time = c.Vector2f(
                            *[fade["fade_in_time"]] * 2
                        )
                    if fade["do_fade_out"]:
                        e_root.particle.fade_out_time = c.Vector2f(
                            *[fade["fade_out_time"]] * 2
                        )

            if "AngleVariance" in emitter:
                e_root.angle_variance = c.Vector2f(*[emitter["AngleVariance"]] * 2)

            if emitter["ParticlesRotate"]:
                e_root.particle.billboard.rotation = c.Vector2f(
                    emitter["ParticleMinStartRotation"],
                    emitter["ParticleMaxStartRotation"],
                )
                e_root.particle.billboard.rotation_speed = c.Vector2f(
                    emitter["ParticleMinStartAngularSpeed"],
                    emitter["ParticleMaxStartAngularSpeed"],
                )

            rotation_type = c.RotationType.parse(emitter["RotationDirectionType"])
            r = e_root.particle.billboard.rotation_speed
            if rotation_type == c.RotationType.RANDOM:
                r = c.Vector2f(
                    -max(abs(r.min), abs(r.max)), max(abs(r.min), abs(r.max))
                )
            elif rotation_type == c.RotationType.COUNTER_CLOCKWISE:
                r = c.Vector2f(
                    max(-abs(r.min), -abs(r.max)), min(-abs(r.min), -abs(r.max))
                )
            elif rotation_type == c.RotationType.CLOCKWISE:
                r = c.Vector2f(abs(r.min), abs(r.max))

            if e_root.type == c.EmitterType.POINT:
                e_root.forward_velocity = c.Vector2f(
                    emitter["ParticleMinStartLinearSpeed"],
                    emitter["ParticleMaxStartLinearSpeed"],
                )

            for i, texture in enumerate(emitter["Textures"]):
                e_root.particle.billboard[f"texture_{i}"] = texture

            e_root.particle.billboard.texture_animation = emitter[
                "textureAnimationName"
            ]

            texture_animation_first_frame = c.TextureAnimationFirstFrames.parse(
                SinsParticle._normalize_animation_spawn_type(
                    emitter["textureAnimationSpawnType"]
                )
            )

            e_root.particle.billboard.texture_animation_first_frame = (
                texture_animation_first_frame
            )
            e_root.particle.billboard.texture_animation_fps = c.Vector2f(
                *[emitter["textureAnimationOnParticleFPS"]] * 2
            )

            if e_root.type == c.EmitterType.RING:

                e_root.radius_x = c.Vector2f(
                    emitter["RingRadiusXMin"], emitter["RingRadiusXMax"]
                )
                e_root.radius_y = c.Vector2f(
                    emitter["RingRadiusYMin"], emitter["RingRadiusYMax"]
                )
                e_root.angle_range = c.Vector2f(
                    emitter["SpawnAngleStart"], emitter["SpawnAngleStop"]
                )

                e_root.tangential_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedTangential"]] * 2
                )

                e_root.use_edge = False
                e_root.normal_offset = c.Vector2f(0, 0)
                e_root.normal_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedRingNormal"]] * 2
                )
                e_root.radial_velocity = c.Vector2f(
                    emitter["ParticleMinStartLinearSpeed"],
                    emitter["ParticleMaxStartLinearSpeed"],
                )
                e_root.angle_range_behavior = c.AngleRangeBehavior.RANDOM

                if not emitter["isSpawnAngleRandom"]:
                    e_root.angle_range_behavior = c.AngleRangeBehavior.SEQUENCE_LOOP
                    e_root.angle_range_sequence_size = emitter[
                        "nonRandomSpawnLoopEmittedParticleCount"
                    ]

            if e_root.type == c.EmitterType.SPHERE:
                for key in ("X", "Y", "Z"):
                    e_root[f"radius_{key.lower()}"] = c.Vector2f(
                        emitter[f"SphereRadius{key}Min"],
                        emitter[f"SphereRadius{key}Max"],
                    )

                e_root.azimuthal_tangential_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedAzimuthalTangential"]] * 2
                )

                e_root.polar_tangential_velocity = c.Vector2f(
                    *[emitter["ParticleMaxStartSpeedPolarTangential"]] * 2
                )
                e_root.latitude_angle_range = c.Vector2f(
                    emitter["SpawnAngleLatitudinalStart"],
                    emitter["SpawnAngleLatitudinalStop"],
                )
                e_root.longitude_angle_range = c.Vector2f(
                    emitter["SpawnAngleLongitudinalStart"],
                    emitter["SpawnAngleLongitudinalStop"],
                )

                e_root.radial_velocity = c.Vector2f(
                    emitter["ParticleMinStartLinearSpeed"],
                    emitter["ParticleMaxStartLinearSpeed"],
                )
                e_root.use_surface = False

            self.emitters.append(e_root)

        for modifier_id, _modifier in enumerate(particle_simulation["Affectors"]):
            modifier = _modifier["AffectorContents"]
            affector_type = _modifier["AffectorType"]

            m_root: c.Modifier = c.Modifier(
                id=modifier_id,
                name=modifier["Name"] or affector_type,
                type=c.ModifierType.parse(
                    SinsParticle._normalize_affector_type(affector_type)
                ),
            )

            if m_root.type == c.ModifierType.DRAG:
                m_root.coefficient_generator = c.CoefficientGenerator()
                m_root.coefficient_generator.range = c.Vector2f(
                    *[modifier["DragCoefficient"]] * 2
                )
            if m_root.type == c.ModifierType.ROTATE_ABOUT_AXIS:
                m_root.type = c.ModifierType.ROTATE
                m_root.axis_of_rotation = c.Vector3f(*modifier["AxisOfRotation"])
                m_root.op = c.Op.AROUND_AXIS
                m_root.axis_origin = c.Vector3f(*modifier["AxisOrigin"])
                m_root.radius = c.Vector2f(*[modifier["Radius"]] * 2)
                m_root.angular_velocity = c.Vector2f(*[modifier["AngularVelocity"]] * 2)
            if m_root.type == c.ModifierType.KILL:
                m_root.point = c.Vector3f(*modifier["Point"])
                m_root.op = c.Op.NEAR_POINT
                m_root.tolerance = c.Vector2f(*[modifier["Distance"]] * 2)
            if m_root.type == c.ModifierType.COLOR:
                m_root.begin_color = modifier["StartColor"]
                m_root.end_color = modifier["EndColor"]
                m_root.will_oscillate = True
                m_root.change_duration = c.Vector2f(*[modifier["TransitionPeriod"]] * 2)
                m_root.change_duration_context = (
                    c.ChangeDurationContext.PARTICLE_TIME_ELAPSED
                )
            if m_root.type == c.ModifierType.SIZE_OSCILLATOR:
                m_root.type = c.ModifierType.SIZE
                m_root.width_stop = c.Vector2f(
                    modifier["BeginSizeX"], modifier["EndSizeX"]
                )
                m_root.height_stop = c.Vector2f(
                    modifier["BeginSizeY"], modifier["EndSizeY"]
                )
            if m_root.type == c.ModifierType.SIZE:
                if {"WidthInflateRate", "HeightInflateRate"} <= modifier.keys():
                    m_root.width_change_rate = c.Vector2f(
                        *[modifier["WidthInflateRate"]] * 2
                    )
                    m_root.height_change_rate = c.Vector2f(
                        *[modifier["HeightInflateRate"]] * 2
                    )
                else:
                    m_root.width_change_rate = c.Vector2f(100, 100)
                    m_root.height_change_rate = c.Vector2f(100, 100)
            if m_root.type == c.ModifierType.LINEAR_BOUNDED_INFLATE:
                m_root.type = c.ModifierType.SIZE
                m_root.width_stop = c.Vector2f(
                    modifier["MinWidth"], modifier["MaxWidth"]
                )
                m_root.height_stop = c.Vector2f(
                    modifier["MinHeight"], modifier["MaxHeight"]
                )
            if m_root.type == c.ModifierType.LINEAR_FORCE_IN_DIRECTION:
                m_root.type = c.ModifierType.PUSH
                m_root.direction = c.Vector3f(*modifier["Direction"])
                m_root.force = c.ModifierForce()
                m_root.force.range = c.Vector2f(
                    modifier["MinForce"], modifier["MaxForce"]
                )
            if m_root.type == c.ModifierType.PUSH:
                m_root.force = c.ModifierForce()
                m_root.force.type = c.ForceType.CONSTANT
                m_root.force.range = c.Vector2f(
                    modifier["MinForce"] / 25, modifier["MaxForce"] / 25
                )
                m_root.op = c.Op.TO_POINT_IN_EFFECT_SPACE  # is it?
                if "Point" in modifier:
                    m_root.point = c.Vector3f(*modifier["Point"])
            if m_root.type == c.ModifierType.JITTER:
                m_root.force = c.ModifierForce()
                m_root.force.type = c.ForceType.RANDOM
                m_root.force.range = c.Vector2f(*[modifier["JitterForce"]] * 2)
                m_root.op = c.Op.RANDOM_JITTER
                if modifier["UseCommonForce"]:
                    m_root.is_random_jitter_shared = modifier["UseCommonForce"]
                m_root.type = c.ModifierType.PUSH

            m_root.start_delay = c.Vector2f(*[modifier["StartTime"]] * 2)

            if modifier["UseOldParticleAffectThreshold"]:
                m_root.particle_time_offset = c.Vector2f(
                    *[modifier["OldParticleAffectThreshold"]] * 2
                )
            if modifier["UseYoungParticleAffectThreshold"]:
                m_root.particle_time_duration = c.Vector2f(
                    *[modifier["YoungParticleAffectThreshold"]] * 2
                )
            if not modifier["HasInfiniteLifeTime"]:
                m_root.duration = c.Vector2f(*[modifier["TotalLifeTime"]] * 2)

            self.modifiers.append(m_root)

    def _build_modifier_to_emitter_attachments(self) -> None:
        fade_counter = 0
        for attacher_id, affector in enumerate(
            self.collector["ParticleSimulation"]["Affectors"]
        ):
            contents = affector["AffectorContents"]

            if "AttachedEmitters" in contents:
                is_fade_affector = affector["AffectorType"].lower() == "fade"
                for attached in contents["AttachedEmitters"]:
                    if is_fade_affector:
                        self.fade_values[fade_counter] = {}
                        self.fade_values[fade_counter][attached] = {
                            "do_fade_in": contents["DoFadeIn"],
                            "do_fade_out": contents["DoFadeOut"],
                            "fade_in_time": contents["FadeInTime"],
                            "fade_out_time": contents["FadeOutTime"],
                        }
                        fade_counter += 1
                    for attachee_id, emitter in enumerate(
                        self.collector["ParticleSimulation"]["Emitters"]
                    ):
                        if (
                            emitter["EmitterContents"]["Name"] == attached
                            and not is_fade_affector
                        ):
                            self.modifier_to_emitter_attachments.append(
                                c.Attacher(attacher_id, attachee_id)
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
        elif value.isdigit():
            value = int(value)

        return value

    @staticmethod
    def _normalize_texture_name(texture_name: str) -> str:
        return os.path.basename(
            texture_name.strip('"')
            .lower()
            .replace(".tga", "")
            .replace(".dds", "")
            .replace("-", "_")
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

    def _curr_line_items(self) -> list[Any]:
        return list(map(self._convert_value, self.curr_line.strip().split(None, 1)))

    @staticmethod
    def _normalize_affector_type(affector_type: str) -> str:
        return {
            "LinearForceToPoint": "PUSH",
            "Jitter": "JITTER",
            "LinearInflate": "SIZE",
            "SizeOscillator": "SIZE_OSCILLATOR",
            "Fade": "FADE",
            "ColorOscillator": "COLOR",
            "LinearForceInDirection": "LINEAR_FORCE_IN_DIRECTION",
            "RotateAboutAxis": "ROTATE_ABOUT_AXIS",
            "KillParticlesNearPoint": "KILL",
            "Drag": "DRAG",
            "LinearBoundedInflate": "LINEAR_BOUNDED_INFLATE",
        }.get(affector_type, affector_type)

    @staticmethod
    def _normalize_animation_spawn_type(spawn_type: str) -> str:
        return {
            "SequentialFrames": "SEQUENTIAL",
            "RandomFrames": "RANDOM",
            "FirstFrame": "FIRST",
        }.get(spawn_type, spawn_type)

    def _delete_fade_affectors(self) -> list[c.Modifier]:
        return [x for x in self.modifiers if x.type != c.ModifierType.FADE]

    def _expect(self, line: str, expected: str) -> None:
        if expected not in line:
            raise SinsParticleFormatException(expected, self.line_number)

    def _next(self, step: int = 1) -> str:
        for _ in range(step):
            self.curr_line = self.f.readline().rstrip("\n")
            self.pos = self.f.tell()
            self.line_number += 1
        return self.curr_line

    def save(
        self, save_path: str = "examples/Ability_CombatNanites.particle_effect"
    ) -> None:
        if self.file:
            with open(save_path, "w") as f:
                json.dump(self.file, f, indent=2)


if __name__ == "__main__":
    colorama.init(autoreset=True)
    try:
        exe_path = os.path.dirname(sys.executable)
        out_path = os.path.join(exe_path, "out")
        if len(sys.argv) < 2:
            print(Fore.RED + "Drop a Sins 1 .particle or a .texanim file\n")
            os.system("pause")
            sys.exit(1)

        os.makedirs(out_path, exist_ok=True)

        for file in sys.argv[1:]:
            file_name = os.path.basename(file)
            name = f"{file_name.split('.')[0]}"

            if file.endswith(".particle"):
                target_path = os.path.join(out_path, "effects")
                extension = ".particle_effect"
            elif file.endswith(".texanim"):
                target_path = os.path.join(out_path, "texture_animations")
                extension = ".texture_animation"
            else:
                print(Fore.WHITE + f"Skipping: {name}")
                continue

            print(
                Fore.WHITE
                + f"{file_name} {Fore.GREEN }→{Fore.WHITE} {name + extension}"
            )
            os.makedirs(target_path, exist_ok=True)
            parser = SinsParticle(particle_path=file).parse()
            parser.save(os.path.join(target_path, name + extension))

        print(Fore.GREEN + "-" * 50 + "Finished" + "-" * 50)
        os.system("pause")
    except Exception as e:
        input(str(e))
