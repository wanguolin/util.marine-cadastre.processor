#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tile Generator
Converts GeoJSON data into map tiles for efficient web visualization.
"""

import os
import json
import subprocess
from pathlib import Path
from tqdm import tqdm


def generate_tiles_from_geojson(
    geojson_path, output_dir, min_zoom=0, max_zoom=14, force_regenerate=False
):
    """
    Generate map tiles from GeoJSON data using Tippecanoe.

    Args:
        geojson_path: Path to the GeoJSON file or directory containing GeoJSON files
        output_dir: Path to output directory for generated tiles
        min_zoom: Minimum zoom level (default: 0)
        max_zoom: Maximum zoom level (default: 14)
        force_regenerate: If True, regenerate tiles even if they already exist
    """
    geojson_path = Path(geojson_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if tippecanoe is installed
    try:
        subprocess.run(["tippecanoe", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: Tippecanoe is not installed or not in PATH.")
        print("Please install Tippecanoe: https://github.com/mapbox/tippecanoe")
        return False

    # Handle both single file and directory inputs
    if geojson_path.is_file():
        files = [geojson_path]
    else:
        files = list(geojson_path.glob("*.geojson"))

    # Track processed and skipped files
    processed_files = 0
    skipped_files = 0

    for file in tqdm(files, desc="Generating tiles"):
        try:
            # Extract base name for the output
            base_name = file.stem
            mbtiles_output = output_dir / f"{base_name}.mbtiles"
            extract_dir = output_dir / base_name

            # Check if output already exists
            if (
                mbtiles_output.exists()
                and extract_dir.exists()
                and not force_regenerate
            ):
                print(
                    f"Skipping {file.name} - output already exists: {mbtiles_output} and {extract_dir}"
                )
                skipped_files += 1
                continue

            # Build tippecanoe command
            cmd = [
                "tippecanoe",
                "-o",
                str(mbtiles_output),
                "-zg",  # Automatically determine zoom levels based on data
                "--drop-densest-as-needed",  # Drop some features at high zoom levels if too dense
                "--extend-zooms-if-still-dropping",  # Extend zoom levels if needed
                "--force",  # Overwrite existing files
                str(file),
            ]

            # Add zoom level constraints if specified
            if min_zoom is not None:
                cmd.extend(["-Z", str(min_zoom)])
            if max_zoom is not None:
                cmd.extend(["-z", str(max_zoom)])

            # Run tippecanoe
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # Extract tiles to directory if needed
            if output_dir:
                extract_dir.mkdir(parents=True, exist_ok=True)

                # Use mb-util to extract tiles
                extract_cmd = [
                    "mb-util",
                    "--image_format=pbf",
                    str(mbtiles_output),
                    str(extract_dir),
                ]

                try:
                    print(f"Extracting tiles: {' '.join(extract_cmd)}")
                    extract_result = subprocess.run(
                        extract_cmd, check=True, capture_output=True, text=True
                    )
                except (subprocess.SubprocessError, FileNotFoundError):
                    print(
                        "Warning: mb-util not found. MBTiles file created but not extracted to directory structure."
                    )
                    print(
                        "Install mb-util to extract tiles: npm install -g @mapbox/mbutil"
                    )

            print(f"Successfully generated tiles for {file}")
            processed_files += 1

        except Exception as e:
            print(f"Error generating tiles for {file}: {str(e)}")
            continue

    print(
        f"Tile generation complete. Processed {processed_files} files, skipped {skipped_files} files."
    )
    return True


def generate_tiles_from_geotiff(
    geotiff_path, output_dir, min_zoom=0, max_zoom=14, force_regenerate=False
):
    """
    Generate map tiles from GeoTIFF data using GDAL.

    Args:
        geotiff_path: Path to the GeoTIFF file or directory containing GeoTIFF files
        output_dir: Path to output directory for generated tiles
        min_zoom: Minimum zoom level (default: 0)
        max_zoom: Maximum zoom level (default: 14)
        force_regenerate: If True, regenerate tiles even if they already exist
    """
    geotiff_path = Path(geotiff_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if gdal is installed
    try:
        subprocess.run(["gdalinfo", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: GDAL is not installed or not in PATH.")
        print("Please install GDAL: https://gdal.org/download.html")
        return False

    # Handle both single file and directory inputs
    if geotiff_path.is_file():
        files = [geotiff_path]
    else:
        files = list(geotiff_path.glob("*.tif"))

    # Track processed and skipped files
    processed_files = 0
    skipped_files = 0

    for file in tqdm(files, desc="Generating tiles from GeoTIFF"):
        try:
            # Extract base name for the output
            base_name = file.stem
            output_path = output_dir / base_name

            # Check if output already exists
            if (
                output_path.exists()
                and any(output_path.iterdir())
                and not force_regenerate
            ):
                print(f"Skipping {file.name} - output already exists: {output_path}")
                skipped_files += 1
                continue

            output_path.mkdir(parents=True, exist_ok=True)

            # Build gdal2tiles command
            cmd = [
                "gdal2tiles.py",
                "--zoom",
                f"{min_zoom}-{max_zoom}",
                "--webviewer=none",  # Don't generate HTML viewer
                "--processes=4",  # Use multiple processes for faster generation
                str(file),
                str(output_path),
            ]

            # Run gdal2tiles
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            print(f"Successfully generated tiles for {file}")
            processed_files += 1

        except Exception as e:
            print(f"Error generating tiles for {file}: {str(e)}")
            continue

    print(
        f"Tile generation complete. Processed {processed_files} files, skipped {skipped_files} files."
    )
    return True


def create_xyz_tiles(
    tif_path, output_dir, min_zoom=0, max_zoom=14, force_regenerate=False
):
    """
    Create XYZ tiles from GeoTIFF using GDAL API.
    This is an alternative implementation using the GDAL Python API.

    Args:
        tif_path: Path to the GeoTIFF file
        output_dir: Path to output directory for generated tiles
        min_zoom: Minimum zoom level (default: 0)
        max_zoom: Maximum zoom level (default: 14)
        force_regenerate: If True, regenerate tiles even if they already exist
    """
    try:
        from osgeo import gdal
    except ImportError:
        print("Error: GDAL Python bindings not installed.")
        print("Please install GDAL Python bindings: pip install gdal")
        return False

    tif_path = Path(tif_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract file name (without extension) for subdirectory
    basename = tif_path.stem
    region_dir = output_dir / basename

    # Check if output already exists
    if region_dir.exists() and any(region_dir.iterdir()) and not force_regenerate:
        print(f"Skipping {tif_path.name} - output already exists: {region_dir}")
        return True

    region_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating tiles for {basename}...")

    try:
        # Open GeoTIFF file
        ds = gdal.Open(str(tif_path))
        if ds is None:
            print(f"Error: Could not open {tif_path}")
            return False

        # Create VRT dataset
        vrt_options = gdal.BuildVRTOptions(resampleAlg="near")
        vrt_ds = gdal.BuildVRT("", [str(tif_path)], options=vrt_options)

        # Create tiles
        gdal.SetConfigOption("GDAL_TIFF_INTERNAL_MASK", "YES")

        # Use gdal.Translate to create tiles
        tile_options = gdal.TranslateOptions(
            format="GTiff",
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE"],
            outputType=gdal.GDT_Byte,
        )

        # Create temporary GeoTIFF file
        temp_tif = region_dir / "temp.tif"
        gdal.Translate(str(temp_tif), vrt_ds, options=tile_options)

        # Use gdal.Warp to reproject to Web Mercator
        warp_options = gdal.WarpOptions(
            dstSRS="EPSG:3857",
            resampleAlg="near",
            multithread=True,
            warpOptions=["NUM_THREADS=ALL_CPUS"],
            creationOptions=["TILED=YES", "COMPRESS=DEFLATE"],
        )

        # Create reprojected GeoTIFF file
        warped_tif = region_dir / "warped.tif"
        gdal.Warp(str(warped_tif), str(temp_tif), options=warp_options)

        # Use gdal2tiles.py for tile generation (more efficient than manual approach)
        cmd = [
            "gdal2tiles.py",
            "--zoom",
            f"{min_zoom}-{max_zoom}",
            "--webviewer=none",
            "--processes=4",
            str(warped_tif),
            str(region_dir),
        ]

        subprocess.run(cmd, check=True)

        # Clean up temporary files
        os.remove(temp_tif)
        os.remove(warped_tif)

        print(f"Successfully created tiles in {region_dir}")
        return True

    except Exception as e:
        print(f"Error creating tiles: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    generate_tiles_from_geojson("path/to/geojson", "path/to/output/tiles")
