import requests
import os
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import box
import gzip
import shutil
from datetime import datetime, timedelta

# === Parámetros de entrada ===
start_date = datetime(2021, 5, 5)
end_date = datetime(2023, 1, 30)  # puedes cambiar la fecha final
save_directory = r'C:\Users\diego\Desktop\CHIRPS_Recortado'

# Área de interés (bounding box)
lon_min, lon_max = -64.5, -63.0
lat_min, lat_max = -22.0, -20.5

# Crear carpeta si no existe
os.makedirs(save_directory, exist_ok=True)

# Crear bounding box como GeoDataFrame
bbox = box(lon_min, lon_max, lat_min, lat_max)
geo = gpd.GeoDataFrame({"geometry": [bbox]}, crs="EPSG:4326")

# === Descarga y recorte día por día ===
current_date = start_date
while current_date <= end_date:
    file_name = f'chirps-v2.0.{current_date.strftime("%Y.%m.%d")}.tif.gz'
    url = f'https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/{current_date.year}/{file_name}'

    print(f"Descargando: {file_name}")
    response = requests.get(url, stream=True)

    if response.status_code == 200:
        gz_path = os.path.join(save_directory, file_name)
        tif_path = gz_path[:-3]  # quitar ".gz"

        # Guardar archivo .gz
        with open(gz_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        # Extraer archivo .tif
        with gzip.open(gz_path, 'rb') as f_in:
            with open(tif_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        os.remove(gz_path)  # borrar el .gz

        # Recortar el raster
        with rasterio.open(tif_path) as src:
            geo = geo.to_crs(src.crs)  # transformar CRS si es necesario
            out_image, out_transform = mask(src, geo.geometry, crop=True)
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })

            clipped_path = os.path.join(
                save_directory,
                f"clipped_{current_date.strftime('%Y%m%d')}.tif"
            )
            with rasterio.open(clipped_path, "w", **out_meta) as dest:
                dest.write(out_image)

        os.remove(tif_path)
        print(f"Guardado: {clipped_path}")
    else:
        print(f"No se pudo descargar: {file_name} | Código: {response.status_code}")

    current_date += timedelta(days=1)