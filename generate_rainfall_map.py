import geopandas as gpd
import pandas as pd
import folium
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import json
import os

# Configuration
RAINFALL_FILE = 'June_2025_Realized.json'
GEOJSON_FILE = 'MAHARASHTRA_DISTRICTS.geojson'
OUTPUT_PNG = 'June_2025_rainfall_map.png'
OUTPUT_HTML = 'June_2025_rainfall_map.html'

def get_color(value):
    """
    Returns color based on rainfall classification.
    """
    if value == 0:
        return '#D3D3D3' # Light Grey - No Rainfall
    elif 0 < value < 64.5:
        return '#FFFFE0' # Light Yellow - Moderate
    elif 64.5 <= value <= 115.5:
        return '#FFA500' # Orange - Heavy
    elif 115.5 < value <= 204.4:
        return '#FF0000' # Red - Very Heavy
    elif value > 204.4:
        return '#8B0000' # Dark Red - Extremely Heavy
    else:
        return '#D3D3D3' # Default/Error

def get_category(value):
    if value == 0:
        return "No Rainfall"
    elif 0 < value < 64.5:
        return "Moderate Rainfall"
    elif 64.5 <= value <= 115.5:
        return "Heavy Rainfall"
    elif 115.5 < value <= 204.4:
        return "Very Heavy Rainfall"
    elif value > 204.4:
        return "Extremely Heavy Rainfall"
    else:
        return "No Data"

def process_data():
    print("Step 1: Processing Rainfall Data...")
    # Load Rainfall Data
    try:
        with open(RAINFALL_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {RAINFALL_FILE}: {e}")
        return None, None

    df = pd.DataFrame(data)
    
    # Check if R/F column exists, otherwise look for alternatives
    if 'R/F' not in df.columns:
        print("Error: 'R/F' column not found in rainfall data.")
        return None, None

    # Convert R/F to numeric, coerce errors to NaN then fill with 0
    df['R/F'] = pd.to_numeric(df['R/F'], errors='coerce').fillna(0)
    
    # Normalize DISTRICT names
    df['DISTRICT'] = df['DISTRICT'].astype(str).str.strip().str.upper()
    
    # Configuration
    GOA_FILE = 'GOA_DISTRICTS.geojson'

    # Manual Name Mapping (New Names -> GeoJSON Old Names)
    name_mapping = {
        'AHILYANAGAR': 'AHMADNAGAR',
        'CHHATRAPATI SAMBHAJI NAGAR': 'AURANGABAD',
        'CHATRAPATI SAMBHAJI NAGAR': 'AURANGABAD', # Variation
        'DHARASHIV': 'OSMANABAD',
        'RAIGAD': 'RAIGARH',
        'SHOLAPUR': 'SOLAPUR',
        'BEED': 'BID',
    }
    
    df['DISTRICT'] = df['DISTRICT'].replace(name_mapping)

    # SPECIAL HANDLING FOR MUMBAI
    if 'MUMBAI' in df['DISTRICT'].values:
        mumbai_row = df[df['DISTRICT'] == 'MUMBAI'].copy()
        if not mumbai_row.empty:
            mumbai_suburban = mumbai_row.copy()
            mumbai_suburban['DISTRICT'] = 'MUMBAI SUBURBAN'
            df = pd.concat([df, mumbai_suburban], ignore_index=True)
            print("Info: Duplicated 'MUMBAI' data to 'MUMBAI SUBURBAN' for map coverage.")

    # Aggregate by District (Mean)
    rain_agg = df.groupby('DISTRICT')['R/F'].mean().reset_index()
    rain_agg.rename(columns={'R/F': 'RAINFALL_MM'}, inplace=True)
    rain_agg['RAINFALL_MM'] = rain_agg['RAINFALL_MM'].round(1)
    
    print(f"Loaded {len(rain_agg)} districts from rainfall data.")

    print("Step 2: Processing GeoJSON Data...")
    # Load Main GeoJSON
    try:
        gdf = gpd.read_file(GEOJSON_FILE)
    except Exception as e:
        print(f"Error loading {GEOJSON_FILE}: {e}")
        return None, None

    # Load Goa GeoJSON
    goa_gdf = None
    if os.path.exists(GOA_FILE):
        try:
            print(f"Loading {GOA_FILE}...")
            goa_gdf = gpd.read_file(GOA_FILE)
        except Exception as e:
            print(f"Error loading {GOA_FILE}: {e}")
    else:
        print(f"Warning: {GOA_FILE} not found. Goa will not be displayed.")

    # Function to find district column
    def find_district_col(geo_df):
        potential_cols = ['dtname', 'district', 'DISTRICT', 'NAME_2', 'Dist_Name', 'Name', 'objectid', 'censuscode']
        for col in geo_df.columns:
            if col.lower() in [p.lower() for p in potential_cols]:
                if pd.api.types.is_string_dtype(geo_df[col]) or pd.api.types.is_object_dtype(geo_df[col]):
                    return col
        return None

    dist_col = find_district_col(gdf)
    if not dist_col:
        print("Error: Could not identify District Name column in Main GeoJSON.")
        return None, None
        
    print(f"Using GeoJSON column '{dist_col}' for district names in Maharashtra.")
    
    # Normalize Main GeoJSON
    gdf['DISTRICT_NORM'] = gdf[dist_col].astype(str).str.strip().str.upper()

    # Process and Merge Goa
    if goa_gdf is not None:
        goa_dist_col = find_district_col(goa_gdf)
        if goa_dist_col:
            print(f"Using GeoJSON column '{goa_dist_col}' for district names in Goa.")
            goa_gdf['DISTRICT_NORM'] = goa_gdf[goa_dist_col].astype(str).str.strip().str.upper()
            
            # Map Goa Districts to match Rainfall Data
            # Rainfall Data has 'GOA' and 'SOUTH GOA'
            # GeoJSON has 'NORTH GOA' and 'SOUTH GOA'
            # Mapping 'NORTH GOA' -> 'GOA' to pick up the generic 'GOA' data
            # 'SOUTH GOA' -> 'SOUTH GOA' (no change needed if matches)
            
            # Use replace with a dict for specific mappings
            goa_mapping = {
                'NORTH GOA': 'GOA'
            }
            goa_gdf['DISTRICT_NORM'] = goa_gdf['DISTRICT_NORM'].replace(goa_mapping)
            
            # Ensure CRS matches before concatenation
            if gdf.crs != goa_gdf.crs:
                goa_gdf = goa_gdf.to_crs(gdf.crs)
            
            # Concatenate
            gdf = pd.concat([gdf, goa_gdf], ignore_index=True)
            print(f"Added {len(goa_gdf)} districts from Goa.")
        else:
            print("Error: Could not identify District Name column in Goa GeoJSON.")

    # Debug matching
    json_districts = set(rain_agg['DISTRICT'])
    geojson_districts = set(gdf['DISTRICT_NORM'])
    
    unmatched_json = json_districts - geojson_districts
    missing_data_map = geojson_districts - json_districts
    
    print("\n--- Matching Report ---")
    if unmatched_json:
        print(f"Districts in JSON but NOT in GeoJSON ({len(unmatched_json)}): {sorted(list(unmatched_json))}")
    else:
        print("All JSON districts matched with GeoJSON.")
        
    if missing_data_map:
        print(f"Districts in GeoJSON with no data in JSON ({len(missing_data_map)}): {sorted(list(missing_data_map))}")
    print("-----------------------\n")

    print("Step 3: Merging Data...")
    # Merge
    merged = gdf.merge(rain_agg, left_on='DISTRICT_NORM', right_on='DISTRICT', how='left')
    
    # Fill missing with 0
    merged['RAINFALL_MM'] = merged['RAINFALL_MM'].fillna(0)
    merged['CATEGORY'] = merged['RAINFALL_MM'].apply(get_category)
    merged['COLOR'] = merged['RAINFALL_MM'].apply(get_color)
    
    # Create a formatted column for tooltip with " mm"
    merged['RAINFALL_DISPLAY'] = merged['RAINFALL_MM'].astype(str) + " mm"
    
    print(f"Merged entries: {len(merged)}")
    return merged, dist_col

def create_static_map(gdf):
    print("Step 4: Generating Static Map (PNG)...")
    fig, ax = plt.subplots(1, 1, figsize=(15, 12)) # Larger figure for clarity
    
    # Plot districts with color
    gdf.plot(column='RAINFALL_MM', ax=ax, color=gdf['COLOR'], edgecolor='black', linewidth=0.8)
    
    # Add labels for districts (centroids)
    # Using apply with a lambda to get representative point for text
    # This might clutter if there are many small districts, but requested "names to all districts"
    # Let's add it for static map too? User asked mostly for interactive "hover", but labeling static is good practice.
    # Actually user said "plz give names... when hover", so static labels might not be strictly required but good.
    # Skipping static labels to keep it "uncluttered" as per original req, unless user insists.
    
    # Custom Legend
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', label='No Rainfall (0 mm)', markerfacecolor='#D3D3D3', markersize=15),
        Line2D([0], [0], marker='s', color='w', label='Moderate (< 64.5 mm)', markerfacecolor='#FFFFE0', markersize=15),
        Line2D([0], [0], marker='s', color='w', label='Heavy (64.5-115.5 mm)', markerfacecolor='#FFA500', markersize=15),
        Line2D([0], [0], marker='s', color='w', label='Very Heavy (115.6-204.4 mm)', markerfacecolor='#FF0000', markersize=15),
        Line2D([0], [0], marker='s', color='w', label='Extremely Heavy (> 204.4 mm)', markerfacecolor='#8B0000', markersize=15),
    ]
    ax.legend(handles=legend_elements, loc='lower right', title="Rainfall Classification", fontsize=10, title_fontsize=12)
    
    ax.set_title("Maharashtra District-wise Rainfall Classification", fontsize=20, pad=20)
    ax.set_axis_off()
    
    plt.savefig(OUTPUT_PNG, dpi=300, bbox_inches='tight')
    print(f"Saved {OUTPUT_PNG}")
    
    OUTPUT_SVG = 'June_2025_rainfall_map.svg'
    plt.savefig(OUTPUT_SVG, format='svg', bbox_inches='tight')
    print(f"Saved {OUTPUT_SVG}")
    plt.close()

def create_interactive_map(gdf, dist_col_name):
    print("Step 5: Generating Interactive Map (HTML)...")
    
    # Centroid of Maharashtra roughly
    m = folium.Map(location=[19.7515, 75.7139], zoom_start=7, tiles='CartoDB positron')
    
    # Style function
    def style_function(feature):
        rainfall = feature['properties'].get('RAINFALL_MM', 0)
        return {
            'fillColor': get_color(rainfall),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7
        }
    
    # Highlight function
    def highlight_function(feature):
        return {
            'fillColor': get_color(feature['properties'].get('RAINFALL_MM',0)),
            'color': 'black',
            'weight': 3,
            'fillOpacity': 0.9
        }

    # Add features
    folium.GeoJson(
        gdf,
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[dist_col_name, 'RAINFALL_DISPLAY', 'CATEGORY'],
            aliases=['District:', 'Rainfall:', 'Category:'],
            localize=True,
            sticky=False
        )
    ).add_to(m)
    
    # Add HTML Legend
    legend_html = '''
     <div style="position: fixed; 
     bottom: 50px; left: 50px; width: 250px; height: 180px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity: 0.9; padding: 10px;">
     <b>Rainfall Classification</b> <br>
     <i style="background:#D3D3D3;opacity:0.7;width:18px;height:18px;display:inline-block;margin-right:8px;border:1px solid #ccc;"></i> No Rainfall (0 mm)<br>
     <i style="background:#FFFFE0;opacity:0.7;width:18px;height:18px;display:inline-block;margin-right:8px;border:1px solid #ccc;"></i> Moderate (&lt; 64.5 mm)<br>
     <i style="background:#FFA500;opacity:0.7;width:18px;height:18px;display:inline-block;margin-right:8px;border:1px solid #ccc;"></i> Heavy (64.5-115.5 mm)<br>
     <i style="background:#FF0000;opacity:0.7;width:18px;height:18px;display:inline-block;margin-right:8px;border:1px solid #ccc;"></i> Very Heavy (115.6-204.4)<br>
     <i style="background:#8B0000;opacity:0.7;width:18px;height:18px;display:inline-block;margin-right:8px;border:1px solid #ccc;"></i> Extr. Heavy (&gt; 204.4)<br>
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add Title Overlay (Optional but nice)
    title_html = '''
     <h3 align="center" style="font-size:20px"><b>Maharashtra District-wise Rainfall Classification</b></h3>
     '''
    m.get_root().html.add_child(folium.Element(title_html))

    m.save(OUTPUT_HTML)
    print(f"Saved {OUTPUT_HTML}")

if __name__ == "__main__":
    merged_gdf, district_col_name = process_data()
    if merged_gdf is not None:
        create_static_map(merged_gdf)
        create_interactive_map(merged_gdf, district_col_name)
        print("Done.")
