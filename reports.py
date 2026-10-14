"""Small PDF report generator; intentionally has no browser/runtime dependency."""
from __future__ import annotations
import base64, io
from pathlib import Path

def build_report(result: dict, output: str | Path) -> Path:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("reportlab is required for PDF reports; install requirements.txt") from exc
    output=Path(output); c=canvas.Canvas(str(output), pagesize=letter); _, h=letter
    c.setTitle("Satellite change analysis"); c.setFont("Helvetica-Bold", 16); c.drawString(42,h-48,"Satellite Change Analysis")
    c.setFont("Helvetica",10); y=h-72
    for text in [f"Location: {result.get('resolved_place_name','Uploaded imagery')}",f"Dates: {result.get('date_before','n/a')} → {result.get('date_after','n/a')}",f"Pipeline: {result.get('pipeline','cnn')}",f"Changed: {result.get('percent_changed',0):.2f}%   Cloud-masked: {result.get('percent_cloud_masked',0):.2f}%"]:
        c.drawString(42,y,text); y-=16
    for key, label in (("image_a_base64","Before"),("image_b_base64","After"),("overlay_base64","Change overlay")):
        encoded=result.get(key)
        if encoded:
            c.drawString(42,y,label); y-=112; c.drawImage(ImageReader(io.BytesIO(base64.b64decode(encoded))),42,y,width=150,height=100,preserveAspectRatio=True,anchor='sw'); y-=12
    c.setFont("Helvetica-Bold",11); c.drawString(42,y,"Regions (type / area px / confidence)"); y-=15; c.setFont("Helvetica",9)
    for region in result.get("change_regions",[])[:12]:
        c.drawString(42,y,f"{region['change_type']} / {region['pixel_area']} / {region['confidence_label']}"); y-=12
    c.setFont("Helvetica-Oblique",8); c.drawString(42,35,"Method: CNN segmentation for uploads; NDVI/NDBI spectral differencing and SCL exclusion for live Sentinel-2."); c.save(); return output
