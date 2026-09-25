import io
import numpy as np
from PIL import Image
from copernicus_client import fetch_satellite_image
from app import run_inference_pipeline, session, preprocess_image

bbox = [77.6600, 12.8400, 77.6900, 12.8650]
date_before = "2017-01-15"
date_after = "2023-01-15"

print("Fetching images...")
img_a_bytes, cloud_before = fetch_satellite_image(bbox, date_before)
img_b_bytes, cloud_after = fetch_satellite_image(bbox, date_after)

print("Saving fetched images to disk...")
with open("test_before.png", "wb") as f:
    f.write(img_a_bytes)
with open("test_after.png", "wb") as f:
    f.write(img_b_bytes)

print(f"Cloud before: {cloud_before}%, Cloud after: {cloud_after}%")

input_a = preprocess_image(img_a_bytes)
input_b = preprocess_image(img_b_bytes)
ort_inputs = {'input_a': input_a, 'input_b': input_b}
ort_outs = session.run(None, ort_inputs)
raw_mask = ort_outs[0] # Shape: [1, 1, 256, 256]

print(f"Raw model output (before sigmoid) - Min: {raw_mask.min():.4f}, Max: {raw_mask.max():.4f}, Mean: {raw_mask.mean():.4f}")

sigmoid_mask = 1 / (1 + np.exp(np.clip(-raw_mask, -88.7, 88.7)))
print(f"Sigmoid output - Min: {sigmoid_mask.min():.4f}, Max: {sigmoid_mask.max():.4f}, Mean: {sigmoid_mask.mean():.4f}")

binary_mask = (sigmoid_mask > 0.5).astype(np.uint8)[0, 0]
changed_pixels = np.sum(binary_mask)
print(f"Pixels > 0.5: {changed_pixels}")

from app import reason_regions
img_a_rgb = np.array(Image.open(io.BytesIO(img_a_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
img_b_rgb = np.array(Image.open(io.BytesIO(img_b_bytes)).convert('RGB').resize((256, 256)), dtype=np.uint8)
change_regions = reason_regions(img_a_rgb, img_b_rgb, binary_mask)

print("Change Regions:")
for r in change_regions:
    print(r)

# Call actual pipeline to see final result
res = run_inference_pipeline(img_a_bytes, img_b_bytes)
print(f"Pipeline percent_changed: {res['percent_changed']}")
