"""Text-Fingerabdruck fuer "nahezu gleiche" Dokumente (F8).

Zwei Dokumente gelten als nahezu gleich, wenn ihr reiner Text identisch ist,
sich die Dateien aber unterscheiden (z. B. nur anderes Speicherdatum, Autor,
eingebettete Vorschau, Komprimierung). Es werden nur Formate ausgewertet,
deren Text sich zuverlaessig auslesen laesst.
"""
from __future__ import annotations

import hashlib
import re
import zipfile
from xml.etree import ElementTree as ET

from .formats import ext_of
from .pathutil import fs

TEXT_EXTS = {"docx", "docm", "dotx", "pptx", "pptm", "ppsx", "xlsx", "xlsm", "odt", "ods", "odp",
             "ott", "txt", "md", "csv", "rtf", "pdf", "html", "htm", "xml", "json"}
MAX_ZIP_MEMBER = 64 * 1024 * 1024
MAX_PLAIN = 32 * 1024 * 1024
_WS = re.compile(r"\s+")


def _xml_text(data: bytes) -> str:
    try:
        root = ET.fromstring(data)  # Standardbibliothek: keine externen Entitaeten
    except ET.ParseError:
        return ""
    return " ".join(t for t in root.itertext() if t and t.strip())


def _zip_texts(path: str, patterns: list[str]) -> list[str]:
    out: list[str] = []
    with zipfile.ZipFile(fs(path)) as z:
        names = sorted(n for n in z.namelist() if any(re.fullmatch(p, n) for p in patterns))
        for n in names:
            info = z.getinfo(n)
            if info.file_size > MAX_ZIP_MEMBER:  # Schutz vor Zip-Bomben
                continue
            out.append(_xml_text(z.read(n)))
    return out


def extract_text(path: str) -> str | None:
    ext = ext_of(path)
    try:
        if ext in ("docx", "docm", "dotx"):
            parts = _zip_texts(path, [r"word/document\.xml", r"word/header\d*\.xml", r"word/footer\d*\.xml",
                                      r"word/footnotes\.xml"])
        elif ext in ("pptx", "pptm", "ppsx"):
            parts = _zip_texts(path, [r"ppt/slides/slide\d+\.xml", r"ppt/notesSlides/notesSlide\d+\.xml"])
        elif ext in ("xlsx", "xlsm"):
            parts = _zip_texts(path, [r"xl/sharedStrings\.xml", r"xl/worksheets/sheet\d+\.xml"])
        elif ext in ("odt", "ods", "odp", "ott"):
            parts = _zip_texts(path, [r"content\.xml"])
        elif ext == "pdf":
            return _pdf_text(path)
        elif ext in ("txt", "md", "csv", "rtf", "html", "htm", "xml", "json"):
            with open(fs(path), "rb") as fh:
                raw = fh.read(MAX_PLAIN + 1)
            if len(raw) > MAX_PLAIN:
                return None
            for enc in ("utf-8-sig", "cp1252", "latin-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return None
        else:
            return None
    except (OSError, zipfile.BadZipFile, KeyError, RuntimeError, ValueError):
        return None
    return " ".join(parts)


def _pdf_text(path: str) -> str | None:
    try:
        import pypdfium2 as pdfium  # optional
    except Exception:
        return None
    try:
        doc = pdfium.PdfDocument(fs(path))
        try:
            texts = []
            for i in range(min(len(doc), 500)):
                page = doc[i]
                tp = page.get_textpage()
                texts.append(tp.get_text_range())
                tp.close()
                page.close()
            return " ".join(texts)
        finally:
            doc.close()
    except Exception:
        return None


def text_fingerprint(path: str) -> str | None:
    """'t:'-Pruefsumme ueber den normalisierten Text, None wenn nicht auswertbar
    oder (fast) leer."""
    txt = extract_text(path)
    if txt is None:
        return None
    norm = _WS.sub(" ", txt).strip().lower()
    if len(norm) < 20:  # zu wenig Text fuer eine sinnvolle Aussage
        return None
    return "t:" + hashlib.blake2b(norm.encode("utf-8", "replace"), digest_size=24).hexdigest()
