#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vessel Tracks Processor
Processes AISVesselTracks data into time-series GeoJSON format suitable for Mapbox visualization.
"""

import os
import json
import geopandas as gpd
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from tqdm import tqdm


def process_vessel_tracks(
    input_path: str,
    output_path: str,
    time_field: str = "TIMESTAMP",
    force_reprocess: bool = False,
):
    """
    Process AIS vessel tracks data into time-series GeoJSON files.

    Args:
        input_path: Path to the input shapefile or directory containing shapefiles
        output_path: Path to output directory for processed GeoJSON files
        time_field: Field name containing timestamp information
        force_reprocess: If True, reprocess files even if output already exists
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Handle both single file and directory inputs
    if input_path.is_file():
        files = [input_path]
    else:
        files = list(input_path.glob("*.shp"))

    # Track processed and skipped files
    processed_files = 0
    skipped_files = 0

    for file in tqdm(files, desc="Processing vessel track files"):
        try:
            # Read the shapefile
            gdf = gpd.read_file(file)

            # Ensure the time field exists
            if time_field not in gdf.columns:
                # Try to extract date from filename
                date_str = extract_date_from_filename(file.stem)
                if date_str:
                    # Check if output file exists
                    output_file = output_path / f"vessel_tracks_{date_str}.geojson"
                    if output_file.exists() and not force_reprocess:
                        print(
                            f"Skipping {file.name} - output already exists: {output_file}"
                        )
                        skipped_files += 1
                        continue

                    # Ensure the CRS is WGS84 (EPSG:4326)
                    if gdf.crs is not None and gdf.crs != "EPSG:4326":
                        gdf = gdf.to_crs("EPSG:4326")
                    elif gdf.crs is None:
                        print(f"Warning: CRS not defined for {file}. Assuming WGS84.")
                        gdf.set_crs("EPSG:4326", inplace=True)

                    # Save to file
                    gdf.to_file(output_file, driver="GeoJSON")
                    processed_files += 1
                    continue
                else:
                    raise ValueError(
                        f"Time field '{time_field}' not found in the data and couldn't extract date from filename"
                    )

            # Convert time field to datetime if it's not already
            gdf[time_field] = pd.to_datetime(gdf[time_field])

            # Ensure the CRS is WGS84 (EPSG:4326)
            if gdf.crs is not None and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            elif gdf.crs is None:
                print(f"Warning: CRS not defined for {file}. Assuming WGS84.")
                gdf.set_crs("EPSG:4326", inplace=True)

            # Group by time periods (e.g., by day)
            grouped = gdf.groupby(gdf[time_field].dt.strftime("%Y-%m-%d"))

            # Process each time period
            for date, group in grouped:
                # Create output filename
                output_file = output_path / f"vessel_tracks_{date}.geojson"

                # Skip if file already exists and not forcing reprocess
                if output_file.exists() and not force_reprocess:
                    print(
                        f"Skipping {date} from {file.name} - output already exists: {output_file}"
                    )
                    skipped_files += 1
                    continue

                # Convert to GeoJSON format with additional properties
                geojson_data = {"type": "FeatureCollection", "features": []}

                for _, row in group.iterrows():
                    # Extract vessel information
                    vessel_info = {
                        "mmsi": str(row.get("MMSI", "")),
                        "vessel_type": str(row.get("VesselType", "")),
                        "vessel_name": str(row.get("VesselName", "")),
                        "length": float(row.get("Length", 0)),
                        "width": float(row.get("Width", 0)),
                        "draft": float(row.get("Draft", 0)),
                        "speed": float(row.get("SOG", 0)),  # Speed Over Ground
                        "course": float(row.get("COG", 0)),  # Course Over Ground
                    }

                    feature = {
                        "type": "Feature",
                        "geometry": json.loads(row.geometry.to_json()),
                        "properties": {
                            "date": date,
                            "timestamp": row[time_field].isoformat(),
                            **vessel_info,
                            # Add any other relevant properties
                            **{
                                k: v
                                for k, v in row.items()
                                if k
                                not in ["geometry", time_field, *vessel_info.keys()]
                            },
                        },
                    }
                    geojson_data["features"].append(feature)

                # Save to file
                with open(output_file, "w") as f:
                    json.dump(geojson_data, f)

                processed_files += 1

        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
            continue

    print(
        f"Processing complete. Processed {processed_files} files, skipped {skipped_files} files. Output saved to {output_path}"
    )


def extract_date_from_filename(filename):
    """Extract date information from filename."""
    # Try to find year in the filename (e.g., 2023 in AISVesselTracks2023)
    import re

    year_match = re.search(r"(\d{4})", filename)
    if year_match:
        return year_match.group(1)
    return None


if __name__ == "__main__":
    # Example usage
    process_vessel_tracks(
        "path/to/input/AISVesselTracks", "path/to/output/vessel_tracks"
    )
