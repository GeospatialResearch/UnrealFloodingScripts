from dataclasses import dataclass
from typing import ClassVar, List, NamedTuple


class Vector(NamedTuple):
    x: float
    y: float
    z: float = 0


@dataclass(frozen=True)
class WaterSource:
    blueprint_class_path: ClassVar[
        str] = "/Game/FluidFlux/Simulation/Modifiers/BP_FluxModifierSourceActor.BP_FluxModifierSourceActor"
    location: Vector = Vector(0, 0, 0)
    volume: float = 1
    intensity: float = 1
    direction: Vector = Vector(0, 0)
