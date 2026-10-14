import base64, io
from pathlib import Path
import pytest
pytest.importorskip("reportlab")
from PIL import Image
from reports import build_report

def test_pdf_report_is_created(tmp_path):
    image=Image.new("RGB",(8,8)); buf=io.BytesIO(); image.save(buf,"PNG")
    result={"percent_changed":1.0,"image_a_base64":base64.b64encode(buf.getvalue()).decode(),"change_regions":[]}
    path=build_report(result,tmp_path/"report.pdf")
    assert path.read_bytes().startswith(b"%PDF")
