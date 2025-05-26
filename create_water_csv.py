from pathlib import Path
from typing import Dict, List

import geopandas as gpd
import pandas as pd
import rioxarray as rxr
import xarray as xr

from models import WaterSource

GAUGE_POINTS_PATH = Path(r"D:\unreal\taumutu\Data\Vector\read_points_1.geojson")
FLOOD_MODEL_OUTPUT_PATH = Path(r"D:\unreal\taumutu\Data\taumutu_100_year.nc")
WATER_SOURCES_OUTPUT_PATH = Path(r"output.csv")
LOCK_TO_GRID = False


def get_gauge_points() -> gpd.GeoDataFrame:
    return gpd.read_file(GAUGE_POINTS_PATH)


def convert_depths_to_water_sources(gauge_depths: gpd.GeoDataFrame) -> List[WaterSource]:
    print(gauge_depths)


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


def extract_depths_for_single_point(row: gpd.GeoSeries, depth_array: xr.DataArray) -> gpd.GeoSeries:
    point_depth_array = depth_array.sel(xx_P0=row.geometry.x, yy_P0=row.geometry.y, method="nearest")
    times = point_depth_array.time.values
    depths_for_times = {}
    for time_slice in times:
        depths_for_times[str(time_slice)] = point_depth_array.sel(time=time_slice).values.item(0)

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
    water_sources = convert_depths_to_water_sources(gauge_depths)
    export_to_csv(gauge_depths, WATER_SOURCES_OUTPUT_PATH)
    print(water_sources)


if __name__ == '__main__':
    main()
