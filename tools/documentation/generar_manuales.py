"""Genera los manuales DOCX a partir de sus fuentes Markdown."""

import re
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MANUALS = (
    "MANUAL_USUARIO_FINAL",
    "MANUAL_TECNICO_FINAL",
    "GUIA_PRESENTACION_FINAL",
)


def add_inline(paragraph, text):
    """Agrega negrita y código corto sin dejar marcas Markdown."""
    parts = re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
        else:
            paragraph.add_run(part)


def markdown_to_docx(source, destination):
    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)

    in_code = False
    code_lines = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                paragraph = document.add_paragraph()
                paragraph.style = document.styles["No Spacing"]
                run = paragraph.add_run("\n".join(code_lines))
                run.font.name = "Consolas"
                run.font.size = Pt(9)
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not line:
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = len(heading.group(1))
            document.add_heading(heading.group(2), level=level - 1 if level > 1 else 0)
            continue
        bullet = re.match(r"^-\s+(.+)$", line)
        if bullet:
            paragraph = document.add_paragraph(style="List Bullet")
            add_inline(paragraph, bullet.group(1))
            continue
        numbered = re.match(r"^\d+\.\s+(.+)$", line)
        if numbered:
            paragraph = document.add_paragraph(style="List Number")
            add_inline(paragraph, numbered.group(1))
            continue
        quote = re.match(r"^>\s+(.+)$", line)
        if quote:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.35)
            run = paragraph.add_run(quote.group(1))
            run.italic = True
            continue
        paragraph = document.add_paragraph()
        add_inline(paragraph, line.replace("  ", ""))

    footer = section.footer.paragraphs[0]
    footer.alignment = 2
    footer.add_run("Pacific Gold · Manual versión 4.0")
    document.save(destination)


def main():
    for name in MANUALS:
        source = DOCS / f"{name}.md"
        destination = DOCS / f"{name}.docx"
        markdown_to_docx(source, destination)
        print(f"Generado: {destination.name}")


if __name__ == "__main__":
    main()
