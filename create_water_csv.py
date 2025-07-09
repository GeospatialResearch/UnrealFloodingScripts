"""Script to read flood model output and points file to create a list of water sources in csv format."""

from pathlib import Path
from typing import Dict, List

import geopandas as gpd
import pandas as pd
import rioxarray as rxr
from shapely.geometry import Point
import xarray as xr

_DATA_ROOT = Path(r"\\file\Research\FloodRiskResearch\Xander\Luke\taumutu_data")
# Path to the file of point locations to query.
GAUGE_POINTS_PATH = Path(r"D:\unreal\taumutu\Data\Vector\read_points_2.geojson")
# Path to the Flood model output .nc file
FLOOD_MODEL_OUTPUT_PATH = _DATA_ROOT / "taumutu_100_year.nc"
# Path to the bounding box of the unreal level, may be smaller than the flood model output
UNREAL_LEVEL_BOUNDS_PATH = _DATA_ROOT / "Taumutu_SW_2k.geojson"
# Path to the output of this script
WATER_SOURCES_OUTPUT_PATH = Path(r"output.csv")
# Whether points should snap to the same grid as the flood model output, or allow arbitrary floating point locations
LOCK_TO_GRID = False


def get_gauge_points() -> gpd.GeoDataFrame:
    """
    Read the file of point locations to be used for querying.

    :return gpd.GeoDataFrame The point locations.
    """
    return gpd.read_file(GAUGE_POINTS_PATH)


def export_to_csv(gauge_depths: gpd.GeoDataFrame, out_file_path: Path) -> None:
    """
    Take the gauge_depth dataframe and export it to a csv file.

    :param gauge_depths gpd.GeoDataFrame The points including Z and data on their depths and times.
    :param out_file_path Path The output csv file.
    """
    gauge_depths["x"] = gauge_depths.geometry.x
    gauge_depths["y"] = gauge_depths.geometry.y
    gauge_depths["z"] = gauge_depths.geometry.z
    # Reorder x,y,z  columns to beginning
    columns = list(gauge_depths)
    columns.insert(0, columns.pop(columns.index("z")))
    columns.insert(0, columns.pop(columns.index("y")))
    columns.insert(0, columns.pop(columns.index("x")))
    gauge_depths = gauge_depths.loc[:, columns]

    gauge_depths = gauge_depths.drop(["geometry"], axis=1)
    gauge_depths.to_csv(out_file_path, index=False)


def transform_gdf_to_unreal_coordinates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts a gpd.GeoDataFrame from CRS in metres to a gpd.GeoDataFrame using unreal CRS (metres, centre of level origin).

    :param gdf: gpd.GeoDataFrame The gdf to be transformed.

    :return gpd.GeoDataFrame The gpd.GeoDataFrame after transformation.
    """
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


def extract_depths_for_single_point(row: gpd.GeoSeries, model_output: xr.Dataset) -> gpd.GeoSeries:
    """
    Takes a single point and queries the model output to get depths and terrain elevation.
    :param row: gpd.GeoSeries The point location.
    :param model_output: xr.Dataset The flood model output
    :return:  gpd.GeoSeries The depths and 3D point.
    """
    point_model_output = model_output.sel(xx_P0=row.geometry.x, yy_P0=row.geometry.y, method="nearest")
    point_depth_array = point_model_output.h_P0
    times = point_model_output.time.values
    depths_for_times = {}
    for time_slice in times:
        depths_for_times[str(time_slice)] = point_depth_array.sel(time=time_slice).values.item(0)
    if LOCK_TO_GRID:
        # Modify point to be centred on raster cell
        x = point_depth_array.xx_P0.values.item(0)
        y = point_depth_array.yy_P0.values.item(0)
    else:
        x = row.geometry.x
        y = row.geometry.y
    z = point_model_output.zb_P0.values.item(0)
    depths_for_times["geometry"] = Point(x, y, z)
    row.update(depths_for_times)
    return row


def extract_depths_for_points(gauge_points: gpd.GeoDataFrame, model_output: xr.Dataset) -> gpd.GeoDataFrame:
    """
    Takes many points and queries the model output to get depths and terrain elevation for each.
    :param gauge_points: gpd.GeoDataFrame The point locations.
    :param model_output: xr.Dataset The flood model output.
    :return: gpd.GeoDataFrame The depths and 3D points.
    """
    point_depths = gauge_points.copy()
    time_slices = model_output.time.values
    for time_slice in time_slices:
        point_depths[str(time_slice)] = pd.Series(dtype='float32')
    point_depths = point_depths.apply(lambda point: extract_depths_for_single_point(point, model_output), axis=1)
    point_depths.drop(["2000-01-01T00:00:00.000000000"], axis=1, inplace=True)
    return point_depths


def main():
    """Script to read flood model output and points file to create a list of water sources in csv format."""
    gauge_points = get_gauge_points()
    with xr.open_dataset(FLOOD_MODEL_OUTPUT_PATH, decode_coords="all") as model_output:
        gauge_depths = extract_depths_for_points(gauge_points, model_output)
    gauge_depths_unreal = transform_gdf_to_unreal_coordinates(gauge_depths)
    export_to_csv(gauge_depths_unreal, WATER_SOURCES_OUTPUT_PATH)


if __name__ == '__main__':
    main()
