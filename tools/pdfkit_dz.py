"""Kleine PDF-Engine (reportlab) im DateiZwilling-Stil."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", FD + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily  # noqa: E402
registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")

ORANGE = colors.HexColor("#f28c28")
DARK = colors.HexColor("#2b2b2b")
HEAD = colors.HexColor("#232323")
GREY = colors.HexColor("#5a5a5a")
LIGHT = colors.HexColor("#f4f4f4")
LINE = colors.HexColor("#d8d8d8")

ST = {
    "p": ParagraphStyle("p", fontName="DV", fontSize=9.6, leading=13.6, textColor=colors.HexColor("#222222"), spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName="DVB", fontSize=15, leading=19, textColor=ORANGE, spaceBefore=10, spaceAfter=6, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DVB", fontSize=11.5, leading=15, textColor=DARK, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "li": ParagraphStyle("li", fontName="DV", fontSize=9.6, leading=13.4, leftIndent=12, bulletIndent=2, spaceAfter=2.5),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.4, leading=11),
    "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8.4, leading=11, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="DVM", fontSize=7.8, leading=10.2, backColor=LIGHT, borderPadding=6,
                           leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=8),
    "quote": ParagraphStyle("quote", fontName="DVI", fontSize=9.4, leading=13.4, leftIndent=10, rightIndent=6,
                            borderColor=ORANGE, borderWidth=0, borderPadding=8, backColor=colors.HexColor("#fff5eb"),
                            spaceBefore=4, spaceAfter=10),
    "note": ParagraphStyle("note", fontName="DV", fontSize=9, leading=12.6, backColor=colors.HexColor("#fff5eb"),
                           borderPadding=7, spaceBefore=4, spaceAfter=10, alignment=TA_LEFT),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(path, title, subtitle, blocks, footer, icon, lang="de"):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=40 * mm, bottomMargin=18 * mm, title=title,
                            author="Stefan J. Kaiser DM5CQ / OE8KKS", subject=subtitle,
                            creator="DateiZwilling 2.0.0")
    W = A4[0] - 36 * mm

    def deco(c, d):
        c.saveState()
        h = 30 * mm
        c.setFillColor(HEAD)
        c.rect(0, A4[1] - h, A4[0], h, stroke=0, fill=1)
        c.setFillColor(ORANGE)
        c.rect(0, A4[1] - h - 1.2 * mm, A4[0], 1.2 * mm, stroke=0, fill=1)
        c.drawImage(icon, 16 * mm, A4[1] - h + 6 * mm, 18 * mm, 18 * mm, mask="auto")
        c.setFont("DVB", 18)
        c.setFillColor(ORANGE)
        c.drawString(38 * mm, A4[1] - 15 * mm, title)
        c.setFont("DV", 9.5)
        c.setFillColor(colors.HexColor("#cfcfcf"))
        c.drawString(38 * mm, A4[1] - 21.5 * mm, subtitle)
        c.setFont("DV", 7.5)
        c.setFillColor(GREY)
        c.drawString(18 * mm, 10 * mm, footer)
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, ("Seite %d" if lang == "de" else "Page %d") % d.page)
        c.restoreState()

    story = []
    for b in blocks:
        kind = b[0]
        if kind == "h1":
            story.append(Paragraph(b[1], ST["h1"]))
        elif kind == "h2":
            story.append(Paragraph(b[1], ST["h2"]))
        elif kind == "p":
            story.append(Paragraph(b[1], ST["p"]))
        elif kind == "note":
            story.append(Paragraph(b[1], ST["note"]))
        elif kind == "quote":
            story.append(Paragraph(esc(b[1]).replace("\n", "<br/>"), ST["quote"]))
        elif kind == "ul":
            for item in b[1]:
                story.append(Paragraph(item, ST["li"], bulletText="•"))
            story.append(Spacer(1, 4))
        elif kind == "ol":
            for i, item in enumerate(b[1], 1):
                story.append(Paragraph(item, ST["li"], bulletText=f"{i}."))
            story.append(Spacer(1, 4))
        elif kind == "code":
            story.append(Preformatted(b[1], ST["code"]))
        elif kind == "img":
            img = Image(b[1])
            ratio = img.imageHeight / img.imageWidth
            wdt = W * b[2] if len(b) > 2 else W
            img.drawWidth, img.drawHeight = wdt, wdt * ratio
            story.append(Spacer(1, 3))
            story.append(img)
            story.append(Spacer(1, 6))
        elif kind == "table":
            head, rows = b[1], b[2]
            widths = b[3] if len(b) > 3 else None
            data = [[Paragraph(h, ST["cellb"]) for h in head]]
            data += [[Paragraph(str(c), ST["cell"]) for c in r] for r in rows]
            cw = [W * x for x in widths] if widths else None
            t = Table(data, colWidths=cw, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, ORANGE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 1), (-1, -1), 0.3, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        elif kind == "keep":
            story.append(KeepTogether([]))
        elif kind == "pb":
            story.append(PageBreak())
        elif kind == "sp":
            story.append(Spacer(1, b[1]))
    doc.build(story, onFirstPage=deco, onLaterPages=deco)
