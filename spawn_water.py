"""Unreal script to spawn water sources at a location based on csv."""

import csv
import os
import pathlib

import unreal

from dataclasses import dataclass
from typing import ClassVar, List, NamedTuple


class Vector(NamedTuple):
    """
    Represents a vector in unreal coordinates, without 3rd party dependencies.
    :arg x: The x component of the vector.
    :arg y: The y component of the vector.
    :arg z: The z component of the vector.
    """
    x: float
    y: float
    z: float = 0


@dataclass(frozen=True)
class WaterSource:
    """
    Represents a water source.
    :arg blueprint_class_path: C;ass
    """
    blueprint_class_path: ClassVar[
        str] = "/Game/FluidFlux/Simulation/Modifiers/BP_FluxModifierSourceActor.BP_FluxModifierSourceActor"
    location: Vector = Vector(0, 0, 0)
    volume: float = 1
    intensity: float = 1
    direction: Vector = Vector(0, 0)


def vector_to_unreal(vector: Vector):
    return unreal.Vector(vector.x, vector.y, vector.z)


def spawn_single_water_source(
    water_source: WaterSource,
    water_source_bp_class: unreal.BlueprintGeneratedClass,
    water_modifier_bp_class: unreal.BlueprintGeneratedClass
):
    """
    Spawns a single water source into an unreal level

    :param water_source: WaterSource The Water Source to spawn
    :param water_source_bp_class: unreal.BlueprintGeneratedClass The unreal blueprint class for a water source.
    :param water_modifier_bp_class: unreal.BlueprintGeneratedClass The blueprint class for a modifier component.
    """
    location = vector_to_unreal(water_source.location)
    rotation = (location - location).rotator()
    # Spawn actor into level
    source_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class=water_source_bp_class,
                                                                    location=location,
                                                                    rotation=rotation)
    # Move actor to specified subfolder
    source_actor.set_folder_path("/FluidFlux/Sources")
    # Modify the water parameters
    modifier_component = source_actor.get_component_by_class(water_modifier_bp_class)
    modifier_component.set_editor_property("volume", water_source.volume)
    mode_enum = modifier_component.get_editor_property("mode")
    modifier_component.set_editor_property("mode", mode_enum.SET)


def spawn_water_sources(water_sources: List[WaterSource]):
    """
    Add a list of water sources into an unreal level.
    :param water_sources: List[WaterSource] The Water Sources to spawn.
    """
    EAL = unreal.EditorAssetLibrary
    blueprint_class = EAL.load_blueprint_class(asset_path=WaterSource.blueprint_class_path)
    component_class = EAL.load_blueprint_class(
        asset_path="/Game/FluidFlux/Simulation/Modifiers/Components/BP_FluxModifierSourceComponent.BP_FluxModifierSourceComponent")
    for water_source in water_sources:
        spawn_single_water_source(water_source, blueprint_class, component_class)


def read_water_sources_csv(csv_path: pathlib.Path) -> List[WaterSource]:
    """
    Read the csv file to get a list of water sources in unreal coordinates.
    :param csv_path: Path to the csv file to read water sources from.
    :return List[WaterSource]: A list of water sources in unreal coordinates.
    """
    water_sources = []
    with open(csv_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        next(csv_reader, None)  # Skip headers
        for x, y, z, *zt in csv_reader:  # Get each water source parameter from the csv
            water_sources.append(
                WaterSource(
                    # Add a water source in cm units, with z adjusted to match unreal level scale
                    Vector(float(x) * 100, float(y) * 100, (float(z) * 181.99 + 1913)),
                    # Set volume to the depth of the water in a hand-picked time slice.
                    volume=float(zt[3]) * 100
                )
            )
    return water_sources


def main():
    """Unreal script to spawn water sources at a location based on csv."""
    file_path = pathlib.Path(__file__).parent / "output.csv"
    water_sources = read_water_sources_csv(file_path)
    spawn_water_sources(water_sources)


if __name__ == '__main__':
    main()
