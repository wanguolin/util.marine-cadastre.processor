#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Marine Cadastre AIS Data Processor
This script processes AIS vessel data from Marine Cadastre into GeoJSON format for Mapbox visualization.
"""

import os
import click
from pathlib import Path
from processors.transit_counts_processor import process_transit_counts
from processors.vessel_tracks_processor import process_vessel_tracks
from processors.tile_generator import (
    generate_tiles_from_geojson,
    generate_tiles_from_geotiff,
)


@click.group()
def cli():
    """Process Marine Cadastre AIS data into Mapbox-compatible formats."""
    pass


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option(
    "--time-field",
    default="BaseDateTime",
    help="Field containing timestamp information",
)
@click.option("--force", is_flag=True, help="Force reprocessing of existing files")
def process_counts(input_path, output_path, time_field, force):
    """Process AISVesselTransitCounts data into time-series GeoJSON."""
    click.echo(f"Processing transit counts from {input_path} to {output_path}")
    process_transit_counts(input_path, output_path, time_field, force_reprocess=force)


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option(
    "--time-field", default="TIMESTAMP", help="Field containing timestamp information"
)
@click.option("--force", is_flag=True, help="Force reprocessing of existing files")
def process_tracks(input_path, output_path, time_field, force):
    """Process AISVesselTracks data into time-series GeoJSON."""
    click.echo(f"Processing vessel tracks from {input_path} to {output_path}")
    process_vessel_tracks(input_path, output_path, time_field, force_reprocess=force)


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option("--min-zoom", default=0, type=int, help="Minimum zoom level")
@click.option("--max-zoom", default=14, type=int, help="Maximum zoom level")
@click.option("--force", is_flag=True, help="Force regeneration of existing tiles")
def generate_tiles(input_path, output_path, min_zoom, max_zoom, force):
    """Generate map tiles from GeoJSON or GeoTIFF data."""
    input_path = Path(input_path)

    if input_path.is_file():
        file_ext = input_path.suffix.lower()
        if file_ext == ".geojson":
            click.echo(f"Generating tiles from GeoJSON: {input_path}")
            generate_tiles_from_geojson(
                input_path, output_path, min_zoom, max_zoom, force_regenerate=force
            )
        elif file_ext in [".tif", ".tiff"]:
            click.echo(f"Generating tiles from GeoTIFF: {input_path}")
            generate_tiles_from_geotiff(
                input_path, output_path, min_zoom, max_zoom, force_regenerate=force
            )
        else:
            click.echo(f"Unsupported file format: {file_ext}")
    else:
        # Check for GeoJSON files first
        geojson_files = list(input_path.glob("*.geojson"))
        if geojson_files:
            click.echo(f"Generating tiles from {len(geojson_files)} GeoJSON files")
            generate_tiles_from_geojson(
                input_path, output_path, min_zoom, max_zoom, force_regenerate=force
            )

        # Check for GeoTIFF files
        tif_files = list(input_path.glob("*.tif")) + list(input_path.glob("*.tiff"))
        if tif_files:
            click.echo(f"Generating tiles from {len(tif_files)} GeoTIFF files")
            generate_tiles_from_geotiff(
                input_path, output_path, min_zoom, max_zoom, force_regenerate=force
            )

        if not geojson_files and not tif_files:
            click.echo(f"No supported files found in {input_path}")


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", type=click.Path())
@click.option(
    "--min-zoom", default=0, type=int, help="Minimum zoom level for tile generation"
)
@click.option(
    "--max-zoom", default=14, type=int, help="Maximum zoom level for tile generation"
)
@click.option("--force", is_flag=True, help="Force reprocessing of existing files")
@click.option(
    "--data-type",
    type=click.Choice(["auto", "counts", "tracks", "both"]),
    default="auto",
    help="Type of data to process: counts, tracks, both, or auto-detect (default)",
)
def process_all(input_path, output_path, min_zoom, max_zoom, force, data_type):
    """Process data and generate tiles in one step."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    # Create output directories
    geojson_dir = output_path / "geojson"
    tiles_dir = output_path / "tiles"
    geojson_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Process data based on input type and data_type option
    if input_path.is_dir():
        # Auto-detect or process specific data types
        process_counts_data = False
        process_tracks_data = False

        # Check for transit counts data
        tif_files = list(input_path.glob("*.tif")) + list(input_path.glob("*.tiff"))
        if tif_files and (data_type in ["auto", "counts", "both"]):
            process_counts_data = True

        # Check for vessel tracks data
        shp_files = list(input_path.glob("*.shp"))
        if shp_files and (data_type in ["auto", "tracks", "both"]):
            process_tracks_data = True

        # If auto-detect didn't find anything but data_type is specified, give a warning
        if data_type in ["counts", "tracks"] and not (
            process_counts_data or process_tracks_data
        ):
            click.echo(
                f"Warning: Specified data type '{data_type}' not found in {input_path}"
            )

        # Process the data
        if process_counts_data:
            click.echo("Processing transit counts data...")
            process_transit_counts(input_path, geojson_dir, force_reprocess=force)

        if process_tracks_data:
            click.echo("Processing vessel tracks data...")
            process_vessel_tracks(input_path, geojson_dir, force_reprocess=force)

    # Generate tiles from processed GeoJSON
    if geojson_dir.exists():
        click.echo(
            f"Generating tiles from processed GeoJSON with zoom levels {min_zoom}-{max_zoom}..."
        )
        generate_tiles_from_geojson(
            geojson_dir, tiles_dir, min_zoom, max_zoom, force_regenerate=force
        )

    click.echo(f"Processing complete. Output saved to {output_path}")


if __name__ == "__main__":
    cli()
