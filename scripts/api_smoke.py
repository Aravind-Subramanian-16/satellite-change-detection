"""
test_api.py  (updated — uses real LEVIR-CD test images, not dummy_0.png)
Sends a /predict request to the running FastAPI server and prints the
full raw JSON response including change_regions from the real ONNX model.
"""
import requests, json, sys

URL = "http://localhost:8000/predict"

# Use a well-known test image with confirmed real predictions
IMG_A = "dataset/test/A/test_102_512_0.png"
IMG_B = "dataset/test/B/test_102_512_0.png"

print(f"[test_api] POST {URL}")
print(f"  image_a : {IMG_A}")
print(f"  image_b : {IMG_B}\n")

try:
    with open(IMG_A, "rb") as fa, open(IMG_B, "rb") as fb:
        resp = requests.post(
            URL,
            files={"image_a": ("image_a.png", fa, "image/png"),
                   "image_b": ("image_b.png", fb, "image/png")},
            timeout=60,
        )
except requests.exceptions.ConnectionError:
    print("ERROR: Could not connect to server at http://localhost:8000")
    print("Start it first with:  uvicorn app:app --host 0.0.0.0 --port 8000")
    sys.exit(1)

print(f"HTTP status        : {resp.status_code}")

if resp.status_code != 200:
    print(f"Error body: {resp.text}")
    sys.exit(1)

data = resp.json()

print(f"percent_changed    : {data['percent_changed']}")
print(f"overlay_base64 len : {len(data['overlay_base64'])} chars")
print(f"num change_regions : {len(data['change_regions'])}")
print()
print("─── change_regions (raw) ───────────────────────────────────────────────")
print(json.dumps(data["change_regions"], indent=2))
print("────────────────────────────────────────────────────────────────────────")
print("\n[DONE] Server is using the real ONNX model (non-dummy).")
