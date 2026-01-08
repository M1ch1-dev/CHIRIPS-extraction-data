import requests
import os
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box
import gzip
import shutil

# --- Entry parameters --- #
start_year = 2001
end_year = 2010
save_directory = r'C:\Users\anon\Desktop\CHIRPS_Recortado'

# --- Área of interest --- #
lon_min, lon_max = -64.5, -63.0  # example: Tarija, Bolivia
lat_min, lat_max = -22.0, -20.5

os.makedirs(save_directory, exist_ok=True)

bbox = box(lon_min, lon_max, lat_min, lat_max)
geo = gpd.GeoDataFrame({"geometry": [bbox]}, crs="EPSG:4326")

# --- Download and cut --- #
for year in range(start_year, end_year + 1):
    for month in range(1, 13):
        file_name = f'chirps-v2.0.{year}.{month:02d}.tif.gz'
        url = f'https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_2-monthly/tifs/{file_name}'

        print(f"Downloading: {file_name}")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            gz_path = os.path.join(save_directory, file_name)
            tif_path = gz_path[:-3]  # remove ".gz"

            # --- document save .gz --- #
            with open(gz_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    if chunk:
                        f.write(chunk)

            # --- Extract .gz --- #
            with gzip.open(gz_path, 'rb') as f_in:
                with open(tif_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            os.remove(gz_path)  # eliminate .gz after extraction

            # --- cut the raster --- #
            with rasterio.open(tif_path) as src:
                geo = geo.to_crs(src.crs) 
                out_image, out_transform = mask(src, geo.geometry, crop=True)
                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform
                })

                clipped_path = os.path.join(save_directory, f"clipped_{year}_{month:02d}.tif")
                with rasterio.open(clipped_path, "w", **out_meta) as dest:
                    dest.write(out_image)

            os.remove(tif_path) 
            print(f"Archive cutted and saved: {clipped_path}")
        else:

            print(f"Fail to download: {file_name} | Código: {response.status_code}")
