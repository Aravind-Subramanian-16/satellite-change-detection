from app import geocode_place
from copernicus_client import make_bbox_square

user_bbox = [77.5581, 13.0696, 77.5583, 13.0699]
square_bbox = make_bbox_square(user_bbox)

print(f"Original bbox (lon_min, lat_min, lon_max, lat_max): {user_bbox}")
print(f"Padded bbox (lon_min, lat_min, lon_max, lat_max):   {square_bbox}")

# Calculate dimensions of the padded bbox in degrees
lon_span = square_bbox[2] - square_bbox[0]
lat_span = square_bbox[3] - square_bbox[1]

# Rough conversion to km (1 degree lat ~= 111.32 km, 1 degree lon at 13 deg N ~= 108.4 km)
print(f"Padded Width:  {lon_span * 108.4:.2f} km")
print(f"Padded Height: {lat_span * 111.32:.2f} km")

