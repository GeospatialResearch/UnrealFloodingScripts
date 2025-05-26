from pathlib import Path
from typing import Dict, List

import geopandas as gpd
import pandas as pd
import rioxarray as rxr
from shapely.geometry import Point
import xarray as xr

from models import Vector, WaterSource

GAUGE_POINTS_PATH = Path(r"D:\unreal\taumutu\Data\Vector\read_points_1.geojson")
FLOOD_MODEL_OUTPUT_PATH = Path(r"D:\unreal\taumutu\Data\taumutu_100_year.nc")
UNREAL_LEVEL_BOUNDS_PATH = Path(r"D:\unreal\taumutu\Data\AoI\Taumutu_SW_2k.geojson")
WATER_SOURCES_OUTPUT_PATH = Path(r"output.csv")
LOCK_TO_GRID = True


def get_gauge_points() -> gpd.GeoDataFrame:
    return gpd.read_file(GAUGE_POINTS_PATH)


def convert_depths_to_water_sources(gauge_depths: gpd.GeoDataFrame) -> List[WaterSource]:
    geometry = gauge_depths.geometry
    depth_column = gauge_depths.iloc[:, 4]  # Get column index 4 as an example of d
    water_sources = [
        WaterSource(location=Vector(x, y), volume=d) for x, y, d in zip(geometry.x, geometry.y, depth_column)
    ]
    return water_sources


def export_to_csv(gauge_depths: gpd.GeoDataFrame, out_file_path: Path) -> None:
    gauge_depths["x"] = gauge_depths.geometry.x
    gauge_depths["y"] = gauge_depths.geometry.y
    # Reorder x and y columns to beginning
    columns = list(gauge_depths)
    columns.insert(0, columns.pop(columns.index("y")))
    columns.insert(0, columns.pop(columns.index("x")))
    gauge_depths = gauge_depths.loc[:, columns]

    gauge_depths = gauge_depths.drop(["geometry"], axis=1)
    gauge_depths.to_csv(out_file_path, index=False)


def transform_gdf_to_unreal_coordinates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    unreal_world_bounds = gpd.read_file(UNREAL_LEVEL_BOUNDS_PATH)
    unreal_origin_location = unreal_world_bounds.geometry.centroid

    assert unreal_origin_location.crs == gdf.crs
    assert all(axis.unit_name == "metre" for axis in unreal_origin_location.crs.axis_info)

    xoff = -unreal_origin_location.geometry.x[0]
    yoff = -unreal_origin_location.geometry.y[0]
    new_geometry = gdf.geometry.translate(xoff, yoff)
    new_geometry = new_geometry.scale(yfact=-1, origin=(0, 0))
    gdf.geometry = new_geometry
    return gdf


def extract_depths_for_single_point(row: gpd.GeoSeries, depth_array: xr.DataArray) -> gpd.GeoSeries:
    point_depth_array = depth_array.sel(xx_P0=row.geometry.x, yy_P0=row.geometry.y, method="nearest")
    times = point_depth_array.time.values
    depths_for_times = {}
    for time_slice in times:
        depths_for_times[str(time_slice)] = point_depth_array.sel(time=time_slice).values.item(0)
    if LOCK_TO_GRID:
        # Modify point to be centred on raster cell
        x = point_depth_array.xx_P0.values.item(0)
        y = point_depth_array.yy_P0.values.item(0)
        depths_for_times["geometry"] = Point(x, y)
    row.update(depths_for_times)
    return row


def extract_depths_for_points(gauge_points: gpd.GeoDataFrame, depth_array: xr.DataArray) -> gpd.GeoDataFrame:
    point_depths = gauge_points.copy()
    time_slices = depth_array.time.values
    for time_slice in time_slices:
        point_depths[str(time_slice)] = pd.Series(dtype='float32')
    point_depths = point_depths.apply(lambda point: extract_depths_for_single_point(point, depth_array), axis=1)
    return point_depths


def main():
    gauge_points = get_gauge_points()
    with xr.open_dataset(FLOOD_MODEL_OUTPUT_PATH, decode_coords="all") as ds:
        depth_array = ds["h_P0"]
        gauge_depths = extract_depths_for_points(gauge_points, depth_array)
    gauge_depths_unreal = transform_gdf_to_unreal_coordinates(gauge_depths)
    water_sources = convert_depths_to_water_sources(gauge_depths_unreal)
    export_to_csv(gauge_depths_unreal, WATER_SOURCES_OUTPUT_PATH)
    print(water_sources)


if __name__ == '__main__':
    main()
