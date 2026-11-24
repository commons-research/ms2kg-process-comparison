"""Render independent zero-based metric panels as standalone SVG."""

from xml.etree import ElementTree as xml


def text(parent, x, y, content, **attributes):
    xml.SubElement(parent, "text", {"x": str(x), "y": str(y), **attributes}).text = content


def render_chart(title, names, metrics, scope):
    width = 960
    baseline = 465
    bar_span = 260
    row_height = 42
    panel_height = 47 + len(names) * row_height
    height = 140 + len(metrics) * panel_height
    chart = xml.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg", "viewBox": f"0 0 {width} {height}",
        "width": str(width), "height": str(height), "role": "img", "aria-labelledby": "title description",
    })
    xml.SubElement(chart, "title", {"id": "title"}).text = title
    xml.SubElement(chart, "desc", {"id": "description"}).text = scope
    xml.SubElement(chart, "style").text = """
        svg { color-scheme: light dark; font: 16px system-ui, sans-serif; background: #fff; color: #172635; --accent: #286d83; }
        @media (prefers-color-scheme: dark) { svg { background: #0d1117; color: #e6edf3; --accent: #65bfd6; } }
        text { fill: currentColor; }
        .heading { font-size: 28px; font-weight: 700; }
        .metric, .value { font-weight: 650; }
        .value { font-variant-numeric: tabular-nums; }
        .muted { fill: var(--muted, currentColor); opacity: .82; }
        .baseline { stroke: var(--border, currentColor); opacity: .45; }
        .name, .value { font-family: ui-monospace, monospace; font-size: 14px; }
        rect { fill: var(--accent, currentColor); opacity: .72; }
    """
    text(chart, 24, 40, title, **{"class": "heading"})
    text(chart, 24, 67, scope, **{"class": "muted"})
    text(chart, 24, 92, "Each panel starts at zero and uses its own scale.", **{"class": "muted"})

    for index, (label, values, number_format) in enumerate(metrics):
        top = 125 + index * panel_height
        group = xml.SubElement(chart, "g", {"role": "group", "aria-label": label})
        text(group, 24, top, label, **{"class": "metric"})
        xml.SubElement(group, "line", {
            "class": "baseline", "x1": str(baseline), "x2": str(baseline),
            "y1": str(top + 12), "y2": str(top + 16 + len(names) * row_height),
        })
        largest = max(values)
        for row, ((name, status), value) in enumerate(zip(names, values, strict=True)):
            y = top + 18 + row * row_height
            text(group, 39, y + 13, name, **{"class": "name"})
            text(group, 39, y + 30, f"{status} pair", **{"class": "muted", "font-size": "13"})
            if value:
                xml.SubElement(group, "rect", {
                    "x": str(baseline), "y": str(y), "width": str(bar_span * (value / largest)),
                    "height": "16", "rx": "3",
                })
            text(group, 936, y + 13, format(value, number_format),
                 **{"text-anchor": "end", "class": "value"})
    return xml.tostring(chart, encoding="utf-8", xml_declaration=True)
