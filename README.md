# IMD District-wise Rainfall Visualization

This project generates **district-wise rainfall classification maps** for the India Meteorological Department (IMD) – Regional Meteorological Centre (RMC), Mumbai.

It produces an **interactive HTML map of India**, with **Maharashtra and Goa districts highlighted**, where each district is color-coded based on **rainfall intensity categories** (Moderate, Heavy, Very Heavy, Extremely Heavy). Hovering over a district displays the **exact rainfall amount (mm)** recorded for the selected month.

## Features
- District-level rainfall visualization for Maharashtra and Goa
- Rainfall intensity classification based on IMD thresholds
- Interactive HTML map with hover tooltips showing:
  - District name
  - Rainfall (mm)
  - Rainfall category
- High-resolution static map export (PNG / SVG)
- Robust handling of district name mismatches and administrative changes

## Tech Stack
- Python
- Pandas, NumPy
- GeoPandas
- Folium
- Matplotlib
- GeoJSON

## Outputs
- Interactive HTML rainfall map
- Static district-wise rainfall classification maps

## Usage
1. Place rainfall JSON data and GeoJSON boundary files in the project directory
2. Update file paths if required
3. Run the Python script to generate maps

## Disclaimer
This project is for academic and research use. Rainfall data may be sampled or anonymized.

---
Developed during internship at **IMD RMC Mumbai**
