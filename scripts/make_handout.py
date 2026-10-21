"""Build the one-page talk handout from saved evidence.

Output: docs/presentation/handout.pdf
No network, no model, no test scoring.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "presentation"
CHART = OUT / "assets" / "f1_vs_resolution_slide.png"
CSV_PATH = ROOT / "degradation_results.csv"
EVIDENCE_PATH = ROOT / "benchmarks" / "results" / "oscd_evidence.json"

NAVY = HexColor("#1F3864")
BLUE = HexColor("#2E75B6")
ORANGE = HexColor("#C55A11")
GREY = HexColor("#595959")
MID = HexColor("#7F7F7F")
INK = HexColor("#262626")
LIGHT_BLUE = HexColor("#EAF1F8")
LIGHT_ORANGE = HexColor("#FBE5D6")
LINE = HexColor("#D9E2F3")

PAGE_W, PAGE_H = A4
MARGIN = 42
CONTENT_W = PAGE_W - 2 * MARGIN


def load_evidence() -> tuple[dict[int, dict[str, float]], dict]:
    agg: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0])
    with CSV_PATH.open(newline="") as handle:
        for row in csv.DictReader(handle):
            values = agg[int(row["factor"])]
            values[0] += int(row["tp"])
            values[1] += int(row["fp"])
            values[2] += int(row["fn"])
    pooled: dict[int, dict[str, float]] = {}
    for factor, (tp, fp, fn) in agg.items():
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        pooled[factor] = {
            "f1": 2 * precision * recall / (precision + recall),
            "precision": precision,
            "recall": recall,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    assert round(pooled[1]["f1"], 4) == 0.8706
    assert round(pooled[4]["f1"], 4) == 0.0441
    assert round(pooled[20]["precision"], 4) == 0.9947
    assert pooled[20]["tp"] + pooled[20]["fp"] == 91006

    evidence = json.loads(EVIDENCE_PATH.read_text())
    assert round(evidence["pooled"]["hardcoded"]["f1"], 4) == 0.0782
    assert round(evidence["pooled"]["percentile"]["f1"], 4) == 0.1176
    assert round(evidence["pooled"]["otsu"]["overall_accuracy"], 4) == 0.3439
    assert round(evidence["pooled"]["cnn_joint"]["f1"], 4) == 0.0007
    return pooled, evidence


def draw_paragraph(renderer, text, x, top, width, style) -> float:
    para = Paragraph(text, style)
    _, height = para.wrap(width, PAGE_H)
    para.drawOn(renderer, x, top - height)
    return top - height


def build() -> Path:
    pooled, evidence = load_evidence()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "handout.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("Resolution-induced performance collapse - one-page handout")
    c.setAuthor("Aravind")

    # Header
    c.setFillColor(ORANGE)
    c.rect(MARGIN, PAGE_H - 88, 5, 52, stroke=0, fill=1)
    kicker = ParagraphStyle(
        "kicker", fontName="Helvetica-Bold", fontSize=8.5, leading=10,
        textColor=ORANGE, alignment=TA_LEFT,
    )
    draw_paragraph(c, "EMPIRICAL CASE STUDY  ·  10-MINUTE TALK", MARGIN + 16,
                   PAGE_H - 48, CONTENT_W - 16, kicker)
    title = ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=21, leading=24,
        textColor=NAVY,
    )
    draw_paragraph(
        c,
        "Resolution-Induced Performance Collapse<br/>of a CNN Change Detector",
        MARGIN + 16, PAGE_H - 58, CONTENT_W - 16, title,
    )
    subtitle = ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=10.5, leading=13,
        textColor=GREY,
    )
    draw_paragraph(
        c,
        "Simulated and real Sentinel-2 evidence from one frozen checkpoint",
        MARGIN + 16, PAGE_H - 118, CONTENT_W - 16, subtitle,
    )
    author = ParagraphStyle(
        "author", fontName="Helvetica", fontSize=8, leading=10, textColor=GREY,
    )
    draw_paragraph(
        c,
        "Aravind  ·  Department of Computer Science and Engineering  ·  "
        "Presidency University, Bengaluru, India",
        MARGIN + 16, PAGE_H - 134, CONTENT_W - 16, author,
    )
    c.setStrokeColor(LINE)
    c.setLineWidth(1)
    c.line(MARGIN, PAGE_H - 146, PAGE_W - MARGIN, PAGE_H - 146)

    heading = ParagraphStyle(
        "heading", fontName="Helvetica-Bold", fontSize=9, leading=11,
        textColor=BLUE,
    )
    body = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=8.6, leading=11.4,
        textColor=INK,
    )
    small = ParagraphStyle(
        "small", fontName="Helvetica", fontSize=7.2, leading=9.2,
        textColor=GREY,
    )
    top = PAGE_H - 164
    top = draw_paragraph(c, "WHAT WE MEASURED", MARGIN, top, CONTENT_W, heading)
    top = draw_paragraph(
        c,
        "One frozen MobileNetV2-based Siamese U-Net, trained once on 0.5 m "
        "LEVIR-CD and never retrained. We blur and resample 2,048 test pairs "
        "to 1, 2, 4, 8 and 10 m, then evaluate the same checkpoint. We also "
        "evaluate it zero-shot on the ten official OSCD test cities "
        "(3,077,936 pixels; 5.17% true change) against train-selected "
        "NDVI/NDBI rules and Otsu. The CNN weights are zero-shot; the "
        "joint-percentile preprocessing was selected on the training cities.",
        MARGIN, top - 6, CONTENT_W, body,
    )

    chart_top = top - 10
    chart_h = CONTENT_W / (9.4 / 5.1)
    chart_y = chart_top - chart_h
    c.drawImage(ImageReader(str(CHART)), MARGIN, chart_y, width=CONTENT_W,
                height=chart_h, preserveAspectRatio=True, anchor="n")

    # Key numbers
    box_top = chart_y - 14
    box_h = 52
    box_w = (CONTENT_W - 16) / 3
    numbers = [
        ("87.06% -> 4.41%", "pooled F1, 0.5 m to 2 m\nunder blur + resampling", ORANGE),
        ("0.068%", "pixels predicted changed at 10 m\n91,006 of 134,217,728", BLUE),
        ("924 / 935", "changed images with zero\npredicted change (98.82%)", HexColor("#2F7D7D")),
    ]
    for index, (value, label, color) in enumerate(numbers):
        x = MARGIN + index * (box_w + 8)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setStrokeColor(LINE)
        c.roundRect(x, box_top - box_h, box_w, box_h, 4, stroke=1, fill=1)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 8, box_top - 19, value)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 6.8)
        lines = label.split("\n")
        for offset, line in enumerate(lines):
            c.drawString(x + 8, box_top - 32 - offset * 8, line)

    oscd_y = box_top - box_h - 18
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(MARGIN, oscd_y, "Real OSCD (ten test cities, 3,077,936 pixels)")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.3)
    c.drawString(
        MARGIN, oscd_y - 13,
        "CNN joint F1 0.0007  ·  percentile 0.1176  ·  hardcoded 0.0782  ·  "
        "Otsu OA 0.3439 (F1 0.0953)",
    )
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawString(
        MARGIN, oscd_y - 26,
        "The test cities had been scored before the reported run. "
        "Descriptive scores, not an independent test.",
    )

    # Claim boundary
    boundary_top = oscd_y - 40
    boundary_h = 74
    c.setFillColor(LIGHT_ORANGE)
    c.roundRect(MARGIN, boundary_top - boundary_h, CONTENT_W, boundary_h, 4,
                stroke=0, fill=1)
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(MARGIN + 10, boundary_top - 16, "CLAIM BOUNDARY")
    c.setFillColor(INK)
    c.setFont("Helvetica", 7.7)
    boundary_lines = [
        "One checkpoint and one training run. Synthetic degradation, not a Sentinel-2 simulation.",
        "OSCD confounds resolution with sensor, geography and season; no SCL in the benchmark.",
        "No causal claim about the real Sentinel-2 gap. No priority or operational claim.",
        "Spectral rules are not a validated fallback. The app is not validated end to end.",
    ]
    for offset, line in enumerate(boundary_lines):
        c.drawString(MARGIN + 10, boundary_top - 31 - offset * 10, line)

    # Footer
    footer_top = boundary_top - boundary_h - 20
    c.setStrokeColor(LINE)
    c.line(MARGIN, footer_top + 8, PAGE_W - MARGIN, footer_top + 8)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 7.8)
    c.drawString(MARGIN, footer_top - 4,
                 "Saved evidence: degradation_results.csv; "
                 "benchmarks/results/oscd_results_v2.json")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGIN, footer_top - 16,
                 "No new test-city scoring was performed for this handout.")
    c.setFillColor(ORANGE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(MARGIN, footer_top - 31,
                 "Paper, code, figures: TODO - insert verified repository URL and DOI.")
    c.setFillColor(MID)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGIN, footer_top - 43,
                 "Draft; citations and PDF build pending. Generated from saved "
                 "results only.")

    c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    out = build()
    print(f"wrote {out}")
