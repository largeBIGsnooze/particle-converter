from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union


class ParticleFacing(Enum):
    FACE_CAMERA = 0
    FACE_PERPENDICULAR = 1
    FACE_PARALLEL = 2


class RotationType(Enum):
    CLOCKWISE = 0
    COUNTER_CLOCKWISE = 1
    RANDOM = 2

    @classmethod
    def parse(cls, direction: int) -> "RotationType":
        return cls(int(direction))


class EmitterType(Enum):
    POINT = auto()
    RING = auto()
    SPHERE = auto()

    @classmethod
    def parse(cls, emitter_type: str) -> "EmitterType":
        return cls[str(emitter_type)]

class ChangeDurationContext(Enum):
    PARTICLE_TIME_ELAPSED = auto()
    MODIFIER_TIME_ELAPSED = auto()

class EmitRateBehavior(Enum):
    SQUARE_WAVE = auto()
    INCREASE = auto()
    DECREASE = auto()


class AngleRangeBehavior(Enum):
    RANDOM = auto()
    SEQUENCE_LOOP = auto()


class ParticleType(Enum):
    BILLBOARD = auto()
    MESH = auto()


class ShaderType(Enum):
    UBER_ONLY_GRADIENT = auto()
    UBER_MULTIPLY_COLOR = auto()
    UBER_ADD_COLOR = auto()
    UBER_OVERLAY_COLOR = auto()


class Anchor(Enum):
    CENTER = 0
    CENTER_LEFT = 1
    CENTER_RIGHT = 2
    TOP_LEFT = 3
    TOP = 4
    TOP_RIGHT = 5
    BOTTOM_RIGHT = 6
    BOTTOM = 7
    BOTTOM_LEFT = 8

    @classmethod
    def parse(cls, anchor: int) -> "Anchor":
        return cls(int(anchor))


class ModifierType(Enum):
    ROTATE = auto()
    PUSH = auto()
    SIZE = auto()
    COLOR = auto()
    FLOAT_PROPERTY = auto()
    DRAG = auto()
    KILL = auto()

    # Sins 1 Specific
    FADE = auto()
    JITTER = auto()
    SIZE_OSCILLATOR = auto()
    LINEAR_FORCE_IN_DIRECTION = auto()
    ROTATE_ABOUT_AXIS = auto()

    @classmethod
    def parse(cls, modifier_type: str) -> "ModifierType":
        return cls[str(modifier_type)]


class ModifierPropertyType(Enum):
    ALPHA = auto()
    WIDTH_AND_HEIGHT_SCALE = auto()
    EROSION_TEST_BASE = auto()
    DISTORTION_SCALAR = auto()
    WIDTH_SCALE = auto()
    HEIGHT_SCALE = auto()
    WIDTH_AND_HEIGHT = auto()


class TextureAnimationFirstFrames(Enum):
    FIRST = auto()
    SEQUENTIAL = auto()
    RANDOM = auto()

    @classmethod
    def parse(cls, frame_type: str) -> "TextureAnimationFirstFrames":
        return cls[str(frame_type)]


class TextureAnimationNextFrames(Enum):
    SEQUENTIAL_LOOP = auto()
    SEQUENTIAL_NO_LOOP = auto()
    RANDOM = auto()
    PING_PONG_LOOP = auto()


class Op(Enum):
    RANDOM_START = auto()
    RANDOM_JITTER = auto()
    RANDOM_JITTER_ON_PLANE = auto()
    RANDOM_JITTER_ON_VECTOR = auto()
    FIXED_IN_PARTICLE_SPACE = auto()
    FIXED_IN_EFFECT_SPACE = auto()
    FIXED_IN_EMITTER_SPACE = auto()
    TO_POINT_IN_EMITTER_SPACE = auto()
    TO_POINT_IN_EFFECT_SPACE = auto()
    # Kill
    NEAR_POINT = auto()


class ForceType(Enum):
    RANDOM = auto()
    CONSTANT = auto()
    EASE = auto()


class ExternalColor(Enum):
    PRIMARY = auto()
    SECONDARY = auto()


class FacingType(Enum):
    FACE_CAMERA = 0
    FACE_CAMERA_BY_ROTATING_ON_PARTICLE_DIRECTION = 1
    FACE_PARTICLE_DIRECTION = 2

    @classmethod
    def parse(cls, facing_type: int) -> "FacingType":
        return cls(int(facing_type))


@dataclass
class Attacher:
    attacher_id: int
    attachee_id: int

    def __serialize__(self) -> dict[str, int]:
        return {"attacher_id": self.attacher_id, "attachee_id": self.attachee_id}


@dataclass
class Vector2f:
    min: float
    max: float

    def __serialize__(self) -> List[float]:
        return [float(self.min), float(self.max)]


@dataclass
class Vector3f:
    x: float
    y: float
    z: float

    def __serialize__(self) -> List[float]:
        return [float(self.x), float(self.y), float(self.z)]


@dataclass
class Node:
    id: int
    name: str
    x: Vector2f
    y: Vector2f
    z: Vector2f
    yaw: Vector2f
    pitch: Vector2f
    roll: Vector2f


@dataclass
class EmitRate:
    primary_emit_rate: Optional[Vector2f] = None
    primary_time: Optional[Vector2f] = None
    secondary_emit_rate: Optional[Vector2f] = None
    secondary_time: Optional[Vector2f] = None
    behavior: Optional[EmitRateBehavior] = None


class MeshShader(Enum):
    BASIC = auto()
    SHIP = auto()
    PLANET_SURFACE = auto()


@dataclass
class Mesh:
    scale: Optional[Vector2f] = None
    mesh: Optional[str] = None
    shader: Optional[MeshShader] = None


@dataclass
class Light:
    type: None
    color: None
    intensity: None
    angle: None
    surface_radius: None


@dataclass
class BasicConstants:
    depth_fade_opacity: Optional[float] = None
    alpha_ramp_curvature: Optional[float] = None
    alpha_ramp_max_alpha_scalar: Optional[float] = None
    depth_fade_distance: Optional[float] = None
    emissive_factor: float = 1
    alpha_ramp_steepness: float = 1
    alpha_ramp_growth_delay: float = 1


@dataclass
class UberConstants:
    basic_constants: BasicConstants
    refraction_constants: Optional[None] = None
    gradient_constants: Optional[None] = None
    erosion_constants: Optional[None] = None
    distortion_constants: Optional[None] = None


@dataclass
class Billboard:
    uber_constants: UberConstants
    rotation: Vector2f = Vector2f(0, 0)
    rotation_speed: Vector2f = Vector2f(0, 0)
    render_with_additive_blending: bool = True
    width: Optional[Vector2f] = None
    height: Optional[Vector2f] = None
    texture_0: Optional[str] = None
    texture_1: Optional[str] = None
    texture_animation_fps: Optional[Vector2f] = None
    texture_animation: Optional[str] = None
    texture_animation_first_frame: Optional[TextureAnimationFirstFrames] = TextureAnimationFirstFrames.RANDOM
    texture_animation_next_frame: Optional[TextureAnimationNextFrames] = TextureAnimationNextFrames.RANDOM
    initial_distortion_scalar: Optional[Vector2f] = None
    random_flip_texture_vertical_chance: Optional[float] = None
    random_flip_texture_horizontal_chance: Optional[float] = None
    initial_refraction_scalar: Optional[Vector2f] = None
    initial_erosion_noise_offset_u: Optional[Vector2f] = None
    initial_erosion_noise_offset_v: Optional[Vector2f] = None
    refraction_mask_texture: Optional[str] = None
    refraction_texture: Optional[str] = None
    erosion_texture: Optional[str] = None
    distortion_texture: Optional[str] = None
    gradient_texture: Optional[str] = None
    facing_type: Union[Optional[FacingType], str] = None
    shader_type: Optional[ShaderType] = None
    anchor: Union[Optional[Anchor], str] = None

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        return None

    def __setitem__(self, key: str, value):
        if hasattr(self, key):
            setattr(self, key, value)
        return None


@dataclass
class Particle:
    billboard: Billboard
    mesh: Mesh
    render_layer: int = 0
    color: Optional[str] = None
    mass: Optional[Vector2f] = None
    max_duration: Optional[Vector2f] = None
    type: Union[Optional[ParticleType], str] = None
    initial_alpha: Optional[Vector2f] = None
    fade_in_time: Optional[Vector2f] = Vector2f(1.0, 1.0)
    fade_out_time: Optional[Vector2f] = Vector2f(1.0, 1.0)
    light: Optional[Light] = None
    external_color: Optional[ExternalColor] = None
    camera_offset: Optional[Vector2f] = None

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        return None

    def __setitem__(self, key: str, value):
        if hasattr(self, key):
            setattr(self, key, value)
        return None


@dataclass
class Emitter:
    id: int
    name: str
    particle: Particle
    emit_rate: EmitRate
    type: Optional[EmitterType] = None
    is_visible: Optional[bool] = None
    emit_start_delay: Optional[Vector2f] = None
    emit_duration: Optional[Vector2f] = None
    emit_max_particle_count: Optional[Vector2f] = None
    emit_particle_count_is_always_one: Optional[bool] = None
    use_surface: Optional[bool] = None
    use_edge: Optional[bool] = None
    radius_x: Optional[Vector2f] = None
    radius_y: Optional[Vector2f] = None
    normal_offset: Optional[Vector2f] = None
    normal_velocity: Optional[Vector2f] = None
    radial_velocity: Optional[Vector2f] = None
    azimuthal_tangential_velocity: Optional[Vector2f] = None
    polar_tangential_velocity: Optional[Vector2f] = None
    latitude_angle_range: Optional[Vector2f] = None
    longitude_angle_range: Optional[Vector2f] = None
    tangential_velocity: Optional[Vector2f] = None
    angle_range: Optional[Vector2f] = None
    angle_range_behavior: Optional[AngleRangeBehavior] = None
    angle_range_sequence_size: Optional[int] = None
    angle_variance: Optional[Vector2f] = None
    forward_velocity: Optional[Vector2f] = None
    radius_z: Optional[Vector2f] = None

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        return None

    def __setitem__(self, key: str, value):
        if hasattr(self, key):
            setattr(self, key, value)
        return None


@dataclass
class ModifierForce:
    range: Optional[Vector2f] = None
    type: Optional[ForceType] = ForceType.CONSTANT


@dataclass
class CoefficientGenerator:
    type: Optional[None] = None
    range: Optional[Vector2f] = None
    easing_function: Optional[None] = None
    easing_values: Optional[Vector2f] = None


@dataclass
class Modifier:
    id: int
    name: str
    type: ModifierType
    force: Optional[ModifierForce] = None
    axis_of_rotation: Optional[Vector3f] = None
    axis_origin: Optional[Vector3f] = None
    radius: Optional[Vector2f] = None
    property_type: Optional[ModifierPropertyType] = None
    op: Optional[Op] = None
    property_value: Optional[None] = None
    coefficient_generator: Optional[CoefficientGenerator] = None
    change_duration_context: Union[Optional[ChangeDurationContext]] = None
    change_duration: Optional[Vector2f] = None
    begin_color: Optional[str] = None
    end_color: Optional[str] = None
    direction: Optional[Vector3f] = None
    start_delay: Optional[Vector2f] = None
    angular_velocity: Optional[Vector2f] = None
    point: Optional[Vector3f] = None
    will_oscillate: Optional[bool] = None
    particle_time_offset: Optional[Vector2f] = None
    width_change_rate: Optional[Vector2f] = None
    width_stop: Optional[Vector2f] = None
    height_stop: Optional[Vector2f] = None
    oscillate_duration: Optional[Vector2f] = None
    height_change_rate: Optional[Vector2f] = None
    particle_time_duration: Optional[Vector2f] = None
    duration: Optional[Vector2f] = None
    is_random_jitter_shared: Optional[bool] = None
    tolerance: Optional[Vector2f] = None


@dataclass
class ParticleEffect:
    version: Optional[int] = 2
    nodes: List[Node] = field(default_factory=list)
    emitters: List[Emitter] = field(default_factory=list)
    modifiers: List[Modifier] = field(default_factory=list)
    emitter_to_node_attachments: List[Dict] = field(default_factory=list)
    modifier_to_emitter_attachments: List[Dict] = field(default_factory=list)


@dataclass
class TextureAnimation:
    texture: Optional[str] = None
    total_frame_count: Optional[int] = None
    column_frame_count: Optional[int] = None
    start_top_left: Optional[List[int]] = None
    frame_size: Optional[List[int]] = None
    frame_stride: Optional[List[int]] = None


@dataclass
class Texanim:
    textureFileName: Optional[str] = None
    numFrames: Optional[int] = None
    numFramesPerRow: Optional[int] = None
    startTopLeft: Optional[List[int]] = None
    frameSize: Optional[List[int]] = None
    frameStride: Optional[List[int]] = None

    def __setitem__(self, key: str, value):
        if hasattr(self, key):
            setattr(self, key, value)
        return None

    def to_texture_animation(self) -> TextureAnimation:
        return TextureAnimation(
            texture=self.textureFileName,
            total_frame_count=self.numFrames,
            column_frame_count=self.numFramesPerRow,
            start_top_left=self.startTopLeft,
            frame_size=self.frameSize,
            frame_stride=self.frameStride,
        )
