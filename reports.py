"""Reproducible PDF report for one completed analysis.

The report opens with a one-page plain-language summary, then repeats the
method, profile, thresholds, scenes, class table, credits, provenance and
honesty notes so a reader can tell what was and was not validated.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    _HAVE_REPORTLAB = True
except ImportError:  # pragma: no cover - exercised only without the dependency
    _HAVE_REPORTLAB = False


FIXED_LIMITATIONS = (
    "Sentinel-2 L2A pixels are 10 m (20 m for some bands); small or narrow features are unresolved.",
    "Single-pair differences can reflect season, moisture, haze, phenology or sensor geometry.",
    "Cloud, shadow and invalid pixels are masked from change statistics but are not inferred.",
    "Change types are deterministic spectral/colour heuristics, not a trained land-cover classifier.",
    "Decision support only. Verify every region against imagery and local knowledge before acting.",
)

THRESHOLD_PLAIN = {
    "ndvi_drop": "Greenness change threshold (NDVI, a −1 to +1 scale)",
    "ndmi_drop": "Moisture change threshold (NDMI, a −1 to +1 scale)",
    "stress_ndvi_drop": "Mild greenness drop counted as crop stress (NDVI)",
    "ndvi_gain": "Greenness gain threshold (NDVI, a −1 to +1 scale)",
    "nbr_drop": "Burn-ratio change threshold (NBR, a −1 to +1 scale)",
    "ndbi_rise": "Built-up index rise threshold (NDBI, a −1 to +1 scale)",
    "bsi_rise": "Bare-soil index rise threshold (BSI, a −1 to +1 scale)",
    "water_ndvi_max": "Water ceiling (NDVI at or below this counts as water)",
    "water_ndmi_max": "Water ceiling (NDMI at or below this counts as water)",
    "mmu_ha": "Smallest patch kept (hectares)",
}


def _format_area(area_ha: float) -> str:
    """Mirror the UI formatter so the PDF shows the same units and numbers."""
    area_ha = float(area_ha)
    area_km2 = area_ha / 100.0
    if area_km2 >= 1:
        return f"{area_km2:.2f} km² ({area_ha:,.0f} ha)"
    if area_ha >= 0.01:
        return f"{area_ha:.2f} ha ({area_ha * 2.47105:.1f} acres)"
    return f"{area_km2 * 1e6:,.0f} m² ({area_ha:.3f} ha)"


def _paragraph(text, style):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def _image(base64_text, width_mm=82, height_mm=62):
    if not base64_text:
        return None
    try:
        raw = base64.b64decode(base64_text)
        reader = io.BytesIO(raw)
        image = PILImage.open(reader)
        image.verify()
        reader.seek(0)
        return Image(reader, width=width_mm * mm, height=height_mm * mm, kind="proportional")
    except Exception:
        return None


def _kv_table(rows, styles, width_mm=170):
    data = [[_paragraph(key, styles["Label"]), _paragraph(value, styles["Body"])] for key, value in rows]
    table = Table(data, colWidths=[42 * mm, (width_mm - 42) * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    return table


def _boxed(story, sentences, styles, fill="#f0fdfa", border="#0f766e"):
    cell = [Paragraph(escape(str(sentence)), styles["Body"]) for sentence in sentences]
    table = Table([[cell]], colWidths=[170 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fill)),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(border)),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)


def _footer(canvas_obj, doc):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 7.5)
    canvas_obj.setFillColor(colors.HexColor("#475569"))
    canvas_obj.drawString(18 * mm, 11 * mm, "Decision support only — not ground truth. Verify before acting.")
    canvas_obj.drawRightString(A4[0] - 18 * mm, 11 * mm, f"Page {doc.page}")
    canvas_obj.restoreState()


def _summary_text(result, styles=None):
    location = result.get("resolved_place_name") or result.get("location") or "the selected area"
    before = result.get("date_before", "the earlier date")
    after = result.get("date_after", "the later date")
    profile_label = result.get("profile_label") or result.get("profile", "general")
    pipeline = result.get("pipeline", "cnn")
    method = "a learned pixel model" if pipeline == "cnn" else "rules that compare two satellite images"
    changed = float(result.get("percent_changed") or 0.0)
    regions = result.get("change_regions") or []
    patch_word = "patch" if len(regions) == 1 else "patches"
    sentences = [
        f"This report compares two images of {location}, one from {before} and one from {after}.",
        f"The {profile_label} profile ({method}) flagged {changed:.2f}% of the pixels as changed, grouped into {len(regions)} {patch_word}.",
    ]
    class_table = result.get("class_table") or {}
    rows = class_table.get("rows") or []
    if rows:
        top = ", ".join(f"{row.get('change_type', 'unknown')} ({_format_area(row.get('area_ha') or 0)})" for row in rows[:3])
        sentences.append(f"Largest detected types: {top}.")
    if result.get("display_metrics"):
        sentences.append(f"Quality: {result.get('validation_status') or 'see the quality section'}.")
    else:
        sentences.append(
            "Quality: this profile has not been tested against labelled data, so the numbers below "
            "are estimates, not measurements. Treat them as hints for where to look."
        )
    sentences.append("Next step: look at the images and the change map, then check the flagged patches before drawing conclusions.")
    return sentences


def _badge_reasons(result):
    reasons = []
    if not result.get("display_metrics"):
        reasons.append("No labelled evaluation exists for this profile, so no performance number is shown anywhere in this report.")
    masked = result.get("percent_cloud_masked")
    if masked is not None:
        reasons.append(f"{float(masked):.2f}% of the pixels were excluded as cloud, shadow or invalid before the statistics were computed.")
    warnings = result.get("warnings") or []
    if warnings:
        reasons.append("The scene-quality notes below also apply to these numbers.")
    return reasons


def _settings_section(result, styles, story):
    meta = result.get("thresholds") or {}
    thresholds = meta.get("thresholds") if isinstance(meta, dict) else None
    for key, value in sorted((thresholds or {}).items()):
        name = THRESHOLD_PLAIN.get(key, f"Rule value “{key}”")
        story.append(_paragraph(f"• {name}: {value}", styles["Body"]))
    mmu = (meta.get("mmu") if isinstance(meta, dict) else None) or {}
    if mmu.get("mmu_ha"):
        story.append(
            _paragraph(
                f"• Patches smaller than {mmu['mmu_ha']} ha were dropped as noise "
                f"({mmu.get('removed_components', 0)} patches removed).",
                styles["Body"],
            )
        )
    for note in result.get("profile_notes") or []:
        story.append(_paragraph("• " + str(note), styles["Body"]))
    provenance_notes = (result.get("provenance") or {}).get("threshold_provenance") or {}
    if provenance_notes:
        story.append(_paragraph("Where these numbers come from", styles["H"]))
        for key, sentence in sorted(provenance_notes.items()):
            story.append(_paragraph(f"• {key}: {sentence}", styles["Small"]))


def _credits_section(result, styles, story):
    story.append(_paragraph("Data and credits", styles["H"]))
    credits = []
    if result.get("pipeline") == "cnn":
        credits.append("Imagery: the two images uploaded by the user (pair mode).")
    else:
        year = str(result.get("date_after") or result.get("date_before") or "")[:4] or "the analysis year"
        credits.append(f"Imagery: contains modified Copernicus Sentinel data [{year}], ESA / European Commission.")
    if result.get("road_context"):
        credits.append("Road data: © OpenStreetMap contributors, Open Database Licence.")
    app_version = (result.get("provenance") or {}).get("app_version")
    credits.append(
        "Report and analysis: generated by the open Satellite change detection app"
        + (f" (version {app_version})" if app_version else "")
        + ", a research prototype for decision support."
    )
    for credit in credits:
        story.append(_paragraph("• " + credit, styles["Small"]))


def build_report(result: dict, output: str | Path) -> Path:
    if not _HAVE_REPORTLAB:
        raise RuntimeError("reportlab is required for PDF reports; install requirements.txt")
    output = Path(output)
    base = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle("TitleX", parent=base["Title"], fontSize=18, leading=22, spaceAfter=4, textColor=colors.HexColor("#0f172a")),
        "Subtitle": ParagraphStyle("SubtitleX", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#475569"), spaceAfter=10),
        "H": ParagraphStyle("HX", parent=base["Heading2"], fontSize=12, leading=15, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#0f766e")),
        "Body": ParagraphStyle("BodyX", parent=base["BodyText"], fontSize=8.5, leading=11),
        "Small": ParagraphStyle("SmallX", parent=base["BodyText"], fontSize=7.5, leading=9.5, textColor=colors.HexColor("#334155")),
        "Label": ParagraphStyle("LabelX", parent=base["BodyText"], fontSize=8.2, leading=10.5, fontName="Helvetica-Bold"),
        "Warn": ParagraphStyle("WarnX", parent=base["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#9a3412")),
        "Badge": ParagraphStyle("BadgeX", parent=base["BodyText"], fontSize=8.5, leading=11, fontName="Helvetica-Bold"),
    }
    story = []
    story.append(_paragraph("Satellite change analysis", styles["Title"]))
    story.append(_paragraph("Decision support report generated by the open satellite-change-detection app.", styles["Subtitle"]))

    story.append(_paragraph("Summary in plain language", styles["H"]))
    _boxed(story, _summary_text(result), styles)

    provenance = result.get("provenance") or {}
    location = result.get("resolved_place_name") or result.get("location") or "Uploaded imagery"
    scenes = result.get("scenes") or {}
    scene_before = (scenes.get("before") or {}).get("id") or ", ".join((provenance.get("scene_ids") or [])[:1]) or "n/a"
    scene_after = (scenes.get("after") or {}).get("id") or ", ".join((provenance.get("scene_ids") or [])[1:2]) or "n/a"
    profile = result.get("profile", "general")
    pipeline = result.get("pipeline", "cnn")
    validation = result.get("validation_status") or "unvalidated, qualitative only"
    aoi = result.get("aoi") or {}
    pixels = aoi.get("expected_pixels") or {}
    changed = float(result.get("percent_changed") or 0.0)
    changed_valid = result.get("percent_changed_valid")
    masked = result.get("percent_cloud_masked")
    rows = [
        ("Location", location),
        ("Profile / pipeline", f"{profile} / {pipeline}"),
        ("Dates", f"{result.get('date_before', 'n/a')} → {result.get('date_after', 'n/a')}"),
        ("Before scene", scene_before),
        ("After scene", scene_after),
        ("Changed pixels", f"{changed:.2f}% of raster" + (f" · {float(changed_valid):.2f}% of valid pixels" if changed_valid is not None else "")),
        ("Cloud/shadow masked", f"{float(masked):.2f}%" if masked is not None else "not reported"),
        ("Regions", str(len(result.get("change_regions") or []))),
        ("AOI", f"{aoi.get('area_km2', 'n/a')} km² · {pixels.get('analysis_width_px', '?')}×{pixels.get('analysis_height_px', '?')} px · ~{pixels.get('pixel_size_x_m', '?')}×{pixels.get('pixel_size_y_m', '?')} m"),
        ("Validation status", validation),
    ]
    story.append(_kv_table(rows, styles))

    badge_color = "#166534" if result.get("display_metrics") else "#9a3412"
    badge_text = (
        "Validation: " + validation
        if result.get("display_metrics")
        else "UNVALIDATED PROFILE — no accuracy number is shown. Use qualitatively only."
    )
    story.append(Spacer(1, 6))
    badge = Table([[_paragraph(badge_text, styles["Badge"])]], colWidths=[170 * mm])
    badge.setStyle(TableStyle([("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(badge_color)), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(badge_color)), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(badge)
    reasons = _badge_reasons(result)
    if reasons:
        story.append(_paragraph("Why this badge", styles["H"]))
        for reason in reasons:
            story.append(_paragraph("• " + reason, styles["Body"]))

    warnings = result.get("warnings") or []
    if result.get("season_warning") and not any(w.get("code") == "season" for w in warnings):
        warnings = warnings + [{"message": result["season_warning"]}]
    if warnings:
        story.append(_paragraph("Warnings", styles["H"]))
        for warning in warnings[:8]:
            story.append(_paragraph("• " + str(warning.get("message", warning)), styles["Warn"]))

    images = [
        ("Before", result.get("image_a_base64")),
        ("After", result.get("image_b_base64")),
        ("Change map", result.get("overlay_base64")),
        ("Cloud mask", result.get("mask_base64")),
    ]
    rendered = [(label, _image(data)) for label, data in images]
    rendered = [(label, image) for label, image in rendered if image is not None]
    if rendered:
        story.append(_paragraph("Imagery", styles["H"]))
        for row_start in range(0, len(rendered), 2):
            pair = rendered[row_start : row_start + 2]
            data = [[_paragraph(label, styles["Small"]) for label, _ in pair], [image for _, image in pair]]
            width = 82 * mm if len(pair) == 2 else 170 * mm
            table = Table(data, colWidths=[width / len(pair)] * len(pair))
            table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
            story.append(KeepTogether(table))
        legend = []
        if result.get("overlay_base64"):
            legend.append("Change map: red = pixels the rules flagged as changed, drawn over the after image.")
        if result.get("mask_base64"):
            legend.append("Cloud mask: white = pixels excluded from the statistics (cloud, shadow or invalid).")
        if result.get("image_a_base64"):
            legend.append("Before and after: true-colour views of the two scenes.")
        if legend:
            story.append(_paragraph("Legend", styles["H"]))
            for line in legend:
                story.append(_paragraph("• " + line, styles["Body"]))

    class_table = result.get("class_table") or {}
    class_rows = class_table.get("rows") or []
    if class_rows:
        story.append(_paragraph("What we found, by type", styles["H"]))
        data = [["Change type", "Area", "Share of the area", "Patches"]]
        for row in class_rows:
            data.append([
                _paragraph(row.get("change_type", "unknown"), styles["Small"]),
                _paragraph(_format_area(row.get("area_ha") or 0), styles["Small"]),
                _paragraph(f"{float(row.get('percent_of_aoi') or 0):.2f}%", styles["Small"]),
                _paragraph(str(int(row.get("region_count") or 0)), styles["Small"]),
            ])
        total = class_table.get("total") or {}
        data.append([
            _paragraph("Total", styles["Label"]),
            _paragraph(_format_area(total.get("area_ha") or 0), styles["Label"]),
            _paragraph(f"{float(total.get('percent_of_aoi') or 0):.2f}%", styles["Label"]),
            _paragraph(str(int(total.get("region_count") or 0)), styles["Label"]),
        ])
        table = Table(data, colWidths=[76 * mm, 42 * mm, 27 * mm, 25 * mm], repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
        story.append(table)
        if class_table.get("note"):
            story.append(_paragraph(class_table["note"], styles["Small"]))

    story.append(_paragraph("Method and settings", styles["H"]))
    _settings_section(result, styles, story)
    road = result.get("road_context")
    if road:
        story.append(_paragraph("Road context (context only, not road detection)", styles["H"]))
        story.append(_paragraph(
            f"{road.get('changed_pixels_near_roads', 0)} of {road.get('total_changed_pixels', 0)} changed pixels "
            f"({road.get('percent_changed_within_distance', 0):.2f}%) are within {road.get('distance_m', '?')} m "
            f"of {road.get('road_count', 0)} mapped OSM roads. {road.get('note', '')} "
            f"{road.get('attribution', '')}. {road.get('licence_note', '')}",
            styles["Body"],
        ))

    regions = result.get("change_regions") or []
    if regions:
        story.append(_paragraph("Detected regions (top 20)", styles["H"]))
        data = [["Type", "Area (ha)", "Pixels", "Confidence"]]
        for region in regions[:20]:
            data.append([
                _paragraph(region.get("change_type", "unknown"), styles["Small"]),
                _paragraph(region.get("area_ha", "—"), styles["Small"]),
                _paragraph(region.get("pixel_area", "—"), styles["Small"]),
                _paragraph(region.get("confidence_label", "—"), styles["Small"]),
            ])
        table = Table(data, colWidths=[93 * mm, 25 * mm, 27 * mm, 25 * mm], repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 7.5)]))
        story.append(table)

    story.append(_paragraph("Limitations", styles["H"]))
    for note in FIXED_LIMITATIONS:
        story.append(_paragraph("• " + note, styles["Body"]))

    _credits_section(result, styles, story)

    story.append(_paragraph("Provenance", styles["H"]))
    p_rows = [
        ("Code commit", provenance.get("commit") or "unavailable"),
        ("App version", provenance.get("app_version") or "unavailable"),
        ("Generated (UTC)", provenance.get("timestamp_utc") or "unavailable"),
        ("Pipeline / profile", f"{provenance.get('pipeline', pipeline)} / {provenance.get('profile', profile)}"),
        ("Scene IDs", ", ".join(provenance.get("scene_ids") or []) or "n/a"),
        ("Dates", json.dumps(provenance.get("dates") or {}, default=str)),
        ("Percent masked", provenance.get("percent_masked", masked if masked is not None else "n/a")),
        ("Options", json.dumps(provenance.get("options") or {}, default=str)),
        ("History ID", result.get("history_id", "n/a")),
    ]
    story.append(_kv_table(p_rows, styles))

    document = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm, title="Satellite change analysis")
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output
