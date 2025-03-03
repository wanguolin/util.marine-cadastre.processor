# Marine Cadastre AIS Data Processor

A Python tool for processing Marine Cadastre AIS (Automatic Identification System) vessel data into Mapbox-compatible GeoJSON format and map tiles. This tool helps convert AIS vessel transit counts and vessel tracks data into time-series visualizations.

## Features

- Process AISVesselTransitCounts data into time-series GeoJSON
- Process AISVesselTracks data into time-series GeoJSON
- Generate map tiles from GeoJSON or GeoTIFF data for efficient web visualization
- Support for both single file and directory batch processing
- Automatic time-based data grouping
- Configurable time field mapping
- Progress tracking with tqdm
- Command-line interface with Click
- Skip already processed files to improve efficiency during development
- Customizable zoom levels for tile generation
- Selective data type processing

## Prerequisites

- Python 3.8 or higher
- Required Python packages (install via pip):
  ```bash
  pip install -r requirements.txt
  ```
- For tile generation:
  - [Tippecanoe](https://github.com/mapbox/tippecanoe) (for GeoJSON tile generation)
  - [GDAL](https://gdal.org/download.html) (for GeoTIFF processing and tile generation)
  - [mb-util](https://github.com/mapbox/mbutil) (optional, for extracting MBTiles)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd utils.marine-cadastre.processor
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install external dependencies for tile generation:
   - Tippecanoe (for GeoJSON tile generation):
     ```bash
     # On macOS with Homebrew
     brew install tippecanoe
     
     # On Linux
     git clone https://github.com/mapbox/tippecanoe.git
     cd tippecanoe
     make -j
     make install
     ```
   
   - GDAL (for GeoTIFF processing):
     ```bash
     # On macOS with Homebrew
     brew install gdal
     
     # On Ubuntu/Debian
     sudo apt-get install gdal-bin python3-gdal
     ```
   
   - mb-util (optional, for extracting MBTiles):
     ```bash
     npm install -g @mapbox/mbutil
     ```

## Usage

The tool provides several commands for processing different types of AIS data:

### Processing Transit Counts

```bash
python src/main.py process-counts <input_path> <output_path> [--time-field BaseDateTime] [--force]
```

Example:
```bash
python src/main.py process-counts ./data/AISVesselTransitCounts2023 ./output/transit_counts --force
```

### Processing Vessel Tracks

```bash
python src/main.py process-tracks <input_path> <output_path> [--time-field TIMESTAMP] [--force]
```

Example:
```bash
python src/main.py process-tracks ./data/AISVesselTracks ./output/vessel_tracks --force
```

### Generating Map Tiles

```bash
python src/main.py generate-tiles <input_path> <output_path> [--min-zoom 0] [--max-zoom 14] [--force]
```

Example:
```bash
python src/main.py generate-tiles ./output/transit_counts ./output/tiles --min-zoom 3 --max-zoom 12 --force
```

### All-in-One Processing

```bash
python src/main.py process-all <input_path> <output_path> [--min-zoom 0] [--max-zoom 14] [--force] [--data-type auto|counts|tracks|both]
```

Example:
```bash
python src/main.py process-all ./data/AISVesselTransitCounts2023 ./output --min-zoom 3 --max-zoom 12 --force --data-type counts
```

### Arguments

- `input_path`: Path to input shapefile/GeoTIFF or directory containing files
- `output_path`: Path to output directory for processed files
- `--time-field`: Optional. Field name containing timestamp information
  - Default for transit counts: "BaseDateTime"
  - Default for vessel tracks: "TIMESTAMP"
- `--min-zoom`: Minimum zoom level for tile generation (default: 0)
- `--max-zoom`: Maximum zoom level for tile generation (default: 14)
- `--force`: Force reprocessing of all files
- `--data-type`: Type of data to process (only for process-all command)
  - `auto`: Auto-detect based on file types (default)
  - `counts`: Process only transit counts data
  - `tracks`: Process only vessel tracks data
  - `both`: Process both data types

## Optimizing Tile Generation

You can control the processing time and output file size by adjusting the zoom levels:

- **Quick processing (smaller files)**: `--min-zoom 3 --max-zoom 10`
- **Balanced**: `--min-zoom 2 --max-zoom 12`
- **High detail (larger files)**: `--min-zoom 0 --max-zoom 14` (default)

## Output Format

### GeoJSON Files

The tool generates daily GeoJSON files with the following naming convention:
- Transit Counts: `transit_counts_YYYY-MM-DD.geojson`
- Vessel Tracks: `vessel_tracks_YYYY-MM-DD.geojson`

#### Transit Counts GeoJSON Properties

- `date`: The date of the data point
- `vessel_count`: Number of unique vessels
- `transit_count`: Number of vessel transits
- Additional fields from the original data

#### Vessel Tracks GeoJSON Properties

- `date`: The date of the track
- `timestamp`: ISO format timestamp
- `mmsi`: Maritime Mobile Service Identity
- `vessel_type`: Type of vessel
- `vessel_name`: Name of vessel
- `length`: Vessel length
- `width`: Vessel width
- `draft`: Vessel draft
- `speed`: Speed Over Ground (SOG)
- `course`: Course Over Ground (COG)
- Additional fields from the original data

### Map Tiles

The tool generates map tiles in two formats:

1. **MBTiles**: A single file containing all tiles in SQLite format
   - Filename: `<basename>.mbtiles`

2. **XYZ Tiles**: Directory structure with tiles organized by zoom/x/y
   - Directory structure: `<basename>/{z}/{x}/{y}.png` or `<basename>/{z}/{x}/{y}.pbf`

## Using with Mapbox

The generated GeoJSON files and map tiles are compatible with Mapbox GL JS. You can use them to create:
- Heatmaps showing vessel density
- Time-series animations of vessel movements
- Point-based vessel visualizations
- Custom styling based on vessel properties

### Loading Tiles in Mapbox GL JS

```javascript
map.addSource('vessel-density', {
  type: 'vector',
  tiles: ['https://your-tile-server.com/tiles/{z}/{x}/{y}.pbf'],
  minzoom: 0,
  maxzoom: 14
});

map.addLayer({
  id: 'vessel-density-layer',
  type: 'heatmap',
  source: 'vessel-density',
  'source-layer': 'vessel_density',
  paint: {
    'heatmap-weight': ['get', 'value'],
    'heatmap-intensity': 1,
    'heatmap-color': [
      'interpolate',
      ['linear'],
      ['heatmap-density'],
      0, 'rgba(0, 0, 255, 0)',
      0.2, 'royalblue',
      0.4, 'cyan',
      0.6, 'lime',
      0.8, 'yellow',
      1, 'red'
    ],
    'heatmap-radius': 10
  }
});
```

## Data Source

The data processed by this tool comes from the Marine Cadastre website:
https://hub.marinecadastre.gov/pages/vesseltraffic

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Marine Cadastre for providing the AIS vessel data
- Mapbox for the visualization platform
- All contributors to the open-source packages used in this project 