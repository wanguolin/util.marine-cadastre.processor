#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Transit Counts Processor
Processes AISVesselTransitCounts data into time-series GeoJSON format suitable for Mapbox visualization.
"""

import os
import json
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping, Point
from pathlib import Path
from datetime import datetime
from tqdm import tqdm


def process_transit_counts(
    input_path: str,
    output_path: str,
    time_field: str = "BaseDateTime",
    force_reprocess: bool = False,
):
    """
    Process AIS vessel transit counts data into time-series GeoJSON files.

    Args:
        input_path: Path to the input shapefile/GeoTIFF or directory containing files
        output_path: Path to output directory for processed GeoJSON files
        time_field: Field name containing timestamp information (for shapefiles)
        force_reprocess: If True, reprocess files even if output already exists
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Handle both single file and directory inputs
    if input_path.is_file():
        files = [input_path]
    else:
        # Look for both shapefiles and GeoTIFF files
        shp_files = list(input_path.glob("*.shp"))
        tif_files = list(input_path.glob("*.tif"))
        files = shp_files + tif_files

    # Track processed and skipped files
    processed_files = 0
    skipped_files = 0

    for file in tqdm(files, desc="Processing transit count files"):
        try:
            file_ext = file.suffix.lower()

            # Check if this file has already been processed
            if file_ext == ".shp":
                # For shapefiles, we need to check if any output files exist with this file's name
                date_str = extract_date_from_filename(file.stem)
                if date_str:
                    output_file = output_path / f"transit_counts_{date_str}.geojson"
                    if output_file.exists() and not force_reprocess:
                        print(
                            f"Skipping {file.name} - output already exists: {output_file}"
                        )
                        skipped_files += 1
                        continue
            elif file_ext == ".tif":
                # For GeoTIFF, check if output file exists
                date_str = extract_date_from_filename(file.stem)
                if date_str:
                    output_file = (
                        output_path / f"transit_counts_{date_str}_{file.stem}.geojson"
                    )
                    if output_file.exists() and not force_reprocess:
                        print(
                            f"Skipping {file.name} - output already exists: {output_file}"
                        )
                        skipped_files += 1
                        continue

            # Process the file based on its type
            if file_ext == ".shp":
                # Process shapefile
                process_shapefile(file, output_path, time_field)
            elif file_ext == ".tif":
                # Process GeoTIFF
                process_geotiff(file, output_path)
            else:
                print(f"Unsupported file format: {file}")
                continue

            processed_files += 1

        except Exception as e:
            print(f"Error processing file {file}: {str(e)}")
            continue

    print(
        f"Processing complete. Processed {processed_files} files, skipped {skipped_files} files. Output saved to {output_path}"
    )


def process_shapefile(file_path, output_path, time_field):
    """Process a shapefile into GeoJSON files grouped by date."""
    # Read the shapefile
    gdf = gpd.read_file(file_path)

    # Ensure the time field exists
    if time_field not in gdf.columns:
        # Try to extract date from filename if time field not found
        date_str = extract_date_from_filename(file_path.stem)
        if date_str:
            # Create a single output file with the extracted date
            output_file = output_path / f"transit_counts_{date_str}.geojson"

            # Ensure the CRS is WGS84 (EPSG:4326)
            if gdf.crs is not None and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")
            elif gdf.crs is None:
                print(f"Warning: CRS not defined for {file_path}. Assuming WGS84.")
                gdf.set_crs("EPSG:4326", inplace=True)

            gdf.to_file(output_file, driver="GeoJSON")
            return
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
        print(f"Warning: CRS not defined for {file_path}. Assuming WGS84.")
        gdf.set_crs("EPSG:4326", inplace=True)

    # Group by time periods (e.g., by day)
    grouped = gdf.groupby(gdf[time_field].dt.strftime("%Y-%m-%d"))

    # Process each time period
    for date, group in grouped:
        # Create output filename
        output_file = output_path / f"transit_counts_{date}.geojson"

        # Skip if file already exists (handled at the higher level)
        if output_file.exists():
            continue

        # Convert to GeoJSON format with additional properties
        geojson_data = {"type": "FeatureCollection", "features": []}

        for _, row in group.iterrows():
            feature = {
                "type": "Feature",
                "geometry": json.loads(row.geometry.to_json()),
                "properties": {
                    "date": date,
                    "vessel_count": int(row.get("VesselCount", 0)),
                    "transit_count": int(row.get("TransitCount", 0)),
                    # Add any other relevant properties
                    **{
                        k: v
                        for k, v in row.items()
                        if k
                        not in ["geometry", time_field, "VesselCount", "TransitCount"]
                    },
                },
            }
            geojson_data["features"].append(feature)

        # Save to file
        with open(output_file, "w") as f:
            json.dump(geojson_data, f)


def process_geotiff(file_path, output_path):
    """Process a GeoTIFF file into GeoJSON format."""
    # Extract date from filename
    date_str = extract_date_from_filename(file_path.stem)
    if not date_str:
        # Use current year if date not found in filename
        date_str = datetime.now().strftime("%Y")

    # Create output filename
    output_file = output_path / f"transit_counts_{date_str}_{file_path.stem}.geojson"

    # Skip if file already exists (handled at the higher level)
    if output_file.exists():
        return

    try:
        # Read the GeoTIFF file metadata
        with rasterio.open(file_path) as src:
            # Get the transform and dimensions
            transform = src.transform
            width = src.width
            height = src.height
            crs = src.crs

            # Create a grid of points for sampling
            # Use a reduced resolution to keep file size manageable
            step = 10  # Sample every 10th pixel
            points = []
            values = []

            # Read the data in a more compatible way
            band = src.read(1, out_dtype="float32")  # Force float32 dtype

            # Sample the raster at regular intervals
            for y in range(0, height, step):
                for x in range(0, width, step):
                    value = band[y, x]
                    if value > 0:  # Only include non-zero values
                        # Convert pixel coordinates to geographic coordinates
                        lon, lat = rasterio.transform.xy(transform, y, x)
                        points.append(Point(lon, lat))
                        values.append(float(value))

            # Create a GeoDataFrame
            gdf = gpd.GeoDataFrame(
                {
                    "geometry": points,
                    "value": values,
                    "date": date_str,
                    "source_file": file_path.name,
                }
            )

            # Set the CRS to match the source GeoTIFF
            if crs:
                gdf.set_crs(crs, inplace=True)
                # Convert to WGS84 (EPSG:4326) for Mapbox compatibility
                gdf = gdf.to_crs("EPSG:4326")
            else:
                print(f"Warning: CRS not defined for {file_path}. Assuming WGS84.")
                gdf.set_crs("EPSG:4326", inplace=True)

            # Save to GeoJSON
            gdf.to_file(output_file, driver="GeoJSON")

    except Exception as e:
        print(f"Error processing GeoTIFF {file_path}: {str(e)}")
        # Try alternative method if the first one fails
        try:
            # Alternative method: convert to point cloud
            convert_tiff_to_point_cloud(file_path, output_file, date_str)
        except Exception as e2:
            print(f"Alternative method also failed: {str(e2)}")
            raise


def convert_tiff_to_point_cloud(file_path, output_file, date_str):
    """Convert a GeoTIFF to a point cloud GeoJSON using GDAL directly."""
    import subprocess
    import tempfile

    # Skip if file already exists (handled at the higher level)
    if output_file.exists():
        return

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_csv:
        temp_csv_path = temp_csv.name

    try:
        # Use gdal_translate to convert to CSV
        cmd = ["gdal_translate", "-of", "CSV", file_path, temp_csv_path]
        subprocess.run(cmd, check=True)

        # Read the CSV file
        df = pd.read_csv(temp_csv_path)

        # Convert to GeoJSON
        if "X" in df.columns and "Y" in df.columns:
            # Create points from X and Y columns
            geometry = [Point(xy) for xy in zip(df["X"], df["Y"])]

            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(
                df.drop(["X", "Y"], axis=1),
                geometry=geometry,
                crs="EPSG:4326",  # Assuming WGS84
            )

            # Add date and source file information
            gdf["date"] = date_str
            gdf["source_file"] = file_path.name

            # Save to GeoJSON
            gdf.to_file(output_file, driver="GeoJSON")
        else:
            raise ValueError("CSV file does not contain X and Y columns")

    finally:
        # Clean up temporary file
        if os.path.exists(temp_csv_path):
            os.unlink(temp_csv_path)


def extract_date_from_filename(filename):
    """Extract date information from filename."""
    # Try to find year in the filename (e.g., 2023 in AISVTC2023Atlantic)
    import re

    year_match = re.search(r"(\d{4})", filename)
    if year_match:
        return year_match.group(1)
    return None


if __name__ == "__main__":
    # Example usage
    process_transit_counts(
        "path/to/input/AISVesselTransitCounts2023", "path/to/output/transit_counts"
    )
