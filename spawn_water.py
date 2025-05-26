import csv
import os
import pathlib

import unreal

from models import Vector, WaterSource

def vector_to_unreal(vector: Vector) -> unreal.Vector:
    return unreal.Vector(vector.x, vector.y, vector.z)


def spawn_water_sources(water_sources: List[WaterSource]):
    EAL = unreal.EditorAssetLibrary
    ELL = unreal.EditorLevelLibrary
    blueprint_class = EAL.load_blueprint_class(asset_path=WaterSource.blueprint_class_path)
    component_class = EAL.load_blueprint_class(asset_path="/Game/FluidFlux/Simulation/Modifiers/Components/BP_FluxModifierSourceComponent.BP_FluxModifierSourceComponent")
    for water_source in water_sources:
        location = vector_to_unreal(water_source.location)
        rotation = (location - location).rotator()
        source_actor = ELL.spawn_actor_from_class(actor_class=blueprint_class,
                                           location=location,
                                           rotation=rotation)
        source_actor.set_folder_path("/FluidFlux/Sources")
        modifier_component = source_actor.get_component_by_class(component_class)
        modifier_component.set_editor_property("volume", water_source.volume)

        print(water_source)


def read_water_sources_csv(csv_path: pathlib.Path) -> List[WaterSource]:
    water_sources = []
    with open(csv_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")
        next(csv_reader, None)  # Skip headers
        for x, y, *zt in csv_reader:
            water_sources.append(WaterSource(Vector(float(x) * 100, float(y) * 100), volume=float(zt[0]) * 100))

    return water_sources


def main():
    file_path = pathlib.Path(__file__).parent / "output.csv"
    water_sources = read_water_sources_csv(file_path)
    spawn_water_sources(water_sources)


if __name__ == '__main__':
    main()
