# Fulcra Skills Support

Python library for visualizing GPS location data from the Fulcra API with both static and interactive maps. Designed to be the foundation for Fulcra-related agent skills.

## Features

- **Authentication**: OAuth2 device flow and token management
- **Data Processing**: Fetch and process location data from Fulcra API  
- **Stay Detection**: Advanced GPS stay detection algorithm
- **Static Visualization**: Generate PNG/SVG maps using Plotly
- **Interactive Visualization**: Create interactive HTML maps using Folium
- **Agent-Friendly**: Simple API designed for easy agent integration

## Installation

```bash
pip install fulcra-skills-support
```

## Quick Start

```python
from fulcra_skills_support import FulcraVisualizer

# Initialize with saved token
viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")

# Generate interactive map for a day
interactive_map = viz.daily_path_interactive("2026-05-09")
viz.save_interactive_map(interactive_map, "daily_path.html")

# Detect stays and visualize
stays = viz.detect_stays("2026-05-09")
combined_map = viz.paths_and_stays_interactive("2026-05-09")
```

## Authentication

### Device Authorization Flow
```python
# For interactive environments (skills)
viz = FulcraVisualizer.from_device_auth()
```

### Token File
```python  
# For agents with saved credentials
viz = FulcraVisualizer.from_token_file("~/.config/fulcra/token.json")
```

## Visualization Methods

### Static Maps (Plotly)
- `daily_path_static(date)` - Basic trajectory line
- `path_by_speed_static(date)` - Color-coded by speed
- `stays_heatmap_static(date)` - Stay locations heatmap

### Interactive Maps (Folium)
- `daily_path_interactive(date)` - Interactive trajectory with popups
- `path_by_speed_interactive(date)` - Color-coded interactive path  
- `stays_heatmap_interactive(date)` - Interactive heatmap with zoom
- `animated_path(date)` - Time-lapse animation
- `directional_flow(date)` - Direction arrows
- `paths_and_stays_interactive(date)` - Combined view

## Stay Detection

```python
# Detect stays for a day
stays = viz.detect_stays("2026-05-09")

# Or from existing location data
viz.load_location_from_file("/tmp/location.parquet")  
stays = viz.detect_stays_from_loaded_data()
```

## Data Exchange

The library uses standardized Parquet formats for data exchange between skills:

### Location Data
```python
viz.save_location_data(data, "/tmp/location.parquet")
viz.load_location_from_file("/tmp/location.parquet")
```

### Stay Data  
```python
viz.save_stays_data(stays, "/tmp/stays.parquet")
viz.load_stays_from_file("/tmp/stays.parquet")
```

## Scope Limitations (v0.1.0)

- **Single-day analysis only** - all methods accept a `date` parameter
- Multi-day comparisons and trend analysis are not implemented
- Future versions may extend to multi-day analysis based on requirements

This focused scope ensures simpler API design, faster implementation, and clear boundaries for the initial release.

## License

MIT License - see LICENSE file for details.