import math

def make_bbox_square(bbox):
    min_lon, min_lat, max_lon, max_lat = bbox
    mid_lat = math.radians((min_lat + max_lat) / 2.0)
    
    deg_lat_to_m = 111320.0
    deg_lon_to_m = 111320.0 * math.cos(mid_lat)
    
    width_m = (max_lon - min_lon) * deg_lon_to_m
    height_m = (max_lat - min_lat) * deg_lat_to_m
    
    max_dim_m = max(width_m, height_m)
    
    target_lon_span = max_dim_m / deg_lon_to_m
    target_lat_span = max_dim_m / deg_lat_to_m
    
    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0
    
    return [
        center_lon - target_lon_span / 2.0,
        center_lat - target_lat_span / 2.0,
        center_lon + target_lon_span / 2.0,
        center_lat + target_lat_span / 2.0
    ]

# test
b = [13.0, 45.0, 14.0, 45.5] # 1 deg lon, 0.5 deg lat
print("Original:", b)
sb = make_bbox_square(b)
print("Square:", sb)

mid_lat = math.radians(45.25)
w = (sb[2]-sb[0]) * 111320.0 * math.cos(mid_lat)
h = (sb[3]-sb[1]) * 111320.0
print("Width (m):", w)
print("Height (m):", h)

