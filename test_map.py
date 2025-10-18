#!/usr/bin/env python3
"""Quick test to check if map HTML is being generated properly."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'ui'))

from interactive_map import create_initial_interactive_map

# Generate map
print("Generating map...")
map_html = create_initial_interactive_map()

print(f"\nMap HTML length: {len(map_html)} characters")
print(f"Contains <html>: {'<html' in map_html}")
print(f"Contains <body>: {'<body' in map_html}")
print(f"Contains folium map: {'leaflet' in map_html.lower()}")
print(f"Contains click handler: {'map_click' in map_html}")

# Save to file for testing
output_file = '/tmp/test_map.html'
with open(output_file, 'w') as f:
    f.write(map_html)

print(f"\nMap saved to: {output_file}")
print(f"Open in browser: file://{output_file}")

# Print first 500 chars
print("\nFirst 500 characters:")
print(map_html[:500])
