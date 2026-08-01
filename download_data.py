import gzip
import io
import urllib.request
import geopandas as gpd
import rioxarray

# 1. URL du fichier CHIRPS compressé
url = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/tifs/p05/2026/chirps-v2.0.2026.06.01.tif.gz"

from datetime import datetime
from zoneinfo import ZoneInfo

# Heure actuelle à Paris / Cotonou / UTC
maintenant_utc = datetime.now(ZoneInfo("UTC"))

maint_str = str(maintenant_utc)
date = maint_str[:10]
heure = maint_str[11:19]
end_date = date + "T" + heure


# 2. Téléchargement du fichier distant et décompression en mémoire
with urllib.request.urlopen(url) as response:
    contenu_gzippe = response.read()
    donnees_tif = gzip.decompress(contenu_gzippe)

# 3. Chargement dans rioxarray depuis le flux binaire décompressé
rds = rioxarray.open_rasterio(io.BytesIO(donnees_tif))

# 4. Définition de l'emprise géographique du Bénin (min_lon, min_lat, max_lon, max_lat)
benin_bbox = [1.6, 6.2, 3.8, 12.4]

# 5. Découpage du raster selon l'emprise du Bénin
benin_clip = rds.rio.clip_box(*benin_bbox)

# 6. Sauvegarde du fichier GeoTIFF découpé
benin_clip.rio.to_raster(f"data/weather/chirps/chirps_benin_{end_date}.tif")
print("Découpage et sauvegarde terminés avec succès !")
