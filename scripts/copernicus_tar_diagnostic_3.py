import requests
import tarfile
import io
import json
from PIL import Image
import numpy as np
from copernicus_client import get_client
from dotenv import load_dotenv

load_dotenv()
client = get_client()
token = client._get_token()
bbox = [77.54639583593094, 13.058251616960113, 77.57000416406906, 13.081248383039885]
p_from, p_to, cloud = client._search_best_scene(bbox, "2023-01-15")
evalscript = """//VERSION=3
function setup() {
  return {
    input: ["B02", "B03", "B04", "B08", "B11"],
    output: [
      { id: "rgb", bands: 3, sampleType: "AUTO" },
      { id: "indices", bands: 3, sampleType: "AUTO" }
    ]
  };
}
function evaluatePixel(sample) {
  let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 0.0001);
  let ndbi = (sample.B11 - sample.B08) / (sample.B11 + sample.B08 + 0.0001);
  return {
    rgb: [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02],
    indices: [0.5 + ndvi / 2.0, 0.5 + ndbi / 2.0, 0]
  };
}
"""
payload = {
    "input": {
        "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
        "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": {"from": p_from, "to": p_to}}}]
    },
    "output": {
        "width": 256, "height": 256,
        "responses": [
            {"identifier": "rgb", "format": {"type": "image/png"}},
            {"identifier": "indices", "format": {"type": "image/png"}}
        ]
    },
    "evalscript": evalscript
}
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/tar"}
resp = requests.post("https://sh.dataspace.copernicus.eu/api/v1/process", headers=headers, json=payload)
tar = tarfile.open(fileobj=io.BytesIO(resp.content))
for name in tar.getnames():
    f = tar.extractfile(name)
    img = Image.open(io.BytesIO(f.read()))
    arr = np.array(img)
    print(f"{name}: shape {arr.shape}, dtype {arr.dtype}, min {arr.min()}, max {arr.max()}")
