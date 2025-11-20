"""Adds timestamps to CSV outputs that are generated from flood model outputs without timestamps."""
import csv
import datetime
import pathlib


def generate_time_stamps_from_band_indices(
    band_indices: list[int],
    reference_datetime: datetime.datetime = datetime.datetime(2000, 1, 1)
) -> list[str]:
    """Takes a list of band indices and creates a list of timestamps based on the index representing hours since reference_datetime."""
    time_columns = []
    for band_index in band_indices:
        hours_since_reference_dt = band_index - 1
        new_datetime = reference_datetime + datetime.timedelta(hours=hours_since_reference_dt)
        formatted_time = new_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")
        time_columns.append(formatted_time)

    return time_columns


def add_timestamps_to_csv(csv_file: pathlib.Path) -> None:
    """Overwrite an existing depth-over-band_index CSV file with timestamps as the columns."""
    # Read all CSV data into memory
    with open(csv_file, "r", newline="") as in_file:
        csv_reader = csv.reader(in_file, delimiter=",")
        xc, yc, zc, *band_index_strs = next(csv_reader)
        remaining_data = list(csv_reader)

    # Prepare new header
    band_indices = [int(band_index) for band_index in band_index_strs]
    time_columns = generate_time_stamps_from_band_indices(band_indices)
    new_header = xc, yc, zc, *time_columns

    # Overwrite CSV with new header that includes timestamps
    with open(csv_file, "w", newline="") as out_file:
        writer = csv.writer(out_file, delimiter=",")
        writer.writerow(new_header)
        writer.writerows(remaining_data)

if __name__ == '__main__':
    add_timestamps_to_csv(pathlib.Path("output.csv"))