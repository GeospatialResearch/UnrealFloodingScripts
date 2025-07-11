"""Unreal script to spawn water sources at a location based on csv."""

import csv
from datetime import datetime
import os
import pathlib

import unreal

from dataclasses import dataclass, field
from typing import ClassVar, List, NamedTuple

# Multiplicative adjustment factor to go from units in metres to UE Landscape scaled units (hand-calibrated)
Z_TERRAIN_SCALE_FACTOR = 1
# Additive adjustment factor to convert Z values to UE landscape units (hand-calibrated)
Z_TERRAIN_INTERCEPT = 0


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


class DepthTimeEntry(NamedTuple):
    timestamp: datetime
    depth: float


@dataclass(frozen=True)
class WaterSource:
    """
    Represents a water source.
    :arg blueprint_class_path: C;ass
    """
    blueprint_class_path: ClassVar[
        str] = "/Game/FFChildren/BP_FluxModifierSourceActor_Child.BP_FluxModifierSourceActor_Child"
    location: Vector = Vector(0, 0, 0)
    depth_array: List[DepthTimeEntry] = field(default_factory=[DepthTimeEntry(datetime.now(), 0.0)])


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
    source_actor.set_actor_scale3d(vector_to_unreal(Vector(1, 1, 1)))
    # Modify the water parameters
    modifier_component = source_actor.get_component_by_class(water_modifier_bp_class)
    modifier_component.set_editor_property("volume", water_source.depth_array[0].depth)
    create_depth_time_curve(source_actor, water_source.depth_array)


def create_depth_time_csv(csv_path: pathlib.Path, depth_array: List[DepthTimeEntry]):
    start_time = depth_array[0].timestamp
    with open(csv_path.as_posix(), "w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        for timestamp, depth in depth_array:
            seconds_since_start = (timestamp - start_time).total_seconds()
            writer.writerow([seconds_since_start, depth])


def create_depth_time_curve(source_actor, depth_array):
    curve_asset_folder = pathlib.Path("/Game/Temp/Curves/")
    curve_asset_name = f"DepthTime_{source_actor.get_actor_label()}"

    temp_csv_folder = pathlib.Path(__file__).parent / "temp"
    temp_csv_folder.mkdir(parents=True, exist_ok=True)
    temp_csv_path = temp_csv_folder / f"{curve_asset_name}.csv"

    create_depth_time_csv(temp_csv_path, depth_array)

    task = unreal.AssetImportTask()
    task.filename = temp_csv_path.as_posix()
    task.destination_path = curve_asset_folder.as_posix()
    task.replace_existing = True
    task.automated = True
    task.save = True

    factory = unreal.CSVImportFactory()

    # Set up import settings
    import_settings = unreal.CSVImportSettings()
    import_settings.import_type = unreal.CSVImportType.ECSV_CURVE_FLOAT
    factory.automated_import_settings = import_settings
    task.factory = factory

    # Perform the import
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    os.remove(temp_csv_path)

    curve_asset = unreal.EditorAssetLibrary.load_asset((curve_asset_folder / curve_asset_name).as_posix())
    imported_asset_path = (curve_asset_folder / curve_asset_name).as_posix()
    curve_asset = unreal.EditorAssetLibrary.load_asset(imported_asset_path)
    source_actor.set_editor_property("DepthTimeCurve", curve_asset)


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
        _xc, _yc, _zc, *time_columns = next(csv_reader)
        time_columns = [datetime.strptime(time_column[:-3], "%Y-%m-%dT%H:%M:%S.%f") for time_column in time_columns]
        for x, y, z, *zt in csv_reader:  # Get each water source parameter from the csv
            water_sources.append(
                WaterSource(
                    # Add a water source in cm units, with z adjusted to match unreal level scale
                    Vector(float(x) * 100, float(y) * 100, (float(z) * Z_TERRAIN_SCALE_FACTOR + Z_TERRAIN_INTERCEPT)),
                    # Set water source depth array in cm
                    depth_array=[DepthTimeEntry(time_columns[i], float(depth_m) * 100) for i, depth_m in enumerate(zt)],
                )
            )
    return water_sources


def main():
    """Unreal script to spawn water sources at a location based on csv."""
    file_path = pathlib.Path(__file__).parent / "testing.csv"
    water_sources = read_water_sources_csv(file_path)
    spawn_water_sources(water_sources)


if __name__ == '__main__':
    main()
