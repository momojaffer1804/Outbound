"""
outbound/backend/extraction/document_parser.py

Document extraction engine to parse academic transcripts, GRE scorecards,
and English test reports (PDF or text) into a structured UserProfile dictionary.
Uses pdfplumber/regex extraction with optional LLM-assisted JSON structuring.
"""

from __future__ import annotations
import re
import os
import io
from typing import Dict, Any, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extracts raw text from PDF file bytes."""
    if not pdfplumber:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception:
            return ""

    text_chunks = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_chunks.append(t)
    return "\n".join(text_chunks)


def parse_academic_document(text: str) -> Dict[str, Any]:
    """
    Parses key admissions parameters from raw document text using regex rules
    with fallback to Groq LLM if available.
    """
    extracted: Dict[str, Any] = {
        "cgpa": None,
        "gre_quant_scaled": None,
        "gre_quant_percentile": None,
        "gre_verbal_percentile": None,
        "gre_awa": None,
        "english_test_type": None,
        "english_score": None,
        "citizenship": None,
        "undergrad_country": None,
        "gate_score_reported": False,
        "undergrad_institution_english_medium": None,
        "detected_fields": []
    }

    if not text.strip():
        return extracted

    # 1. CGPA Extraction
    cgpa_patterns = [
        r'(?:CGPA|Cumulative\s+GPA|GPA|Overall\s+Score)\s*[:=]?\s*([0-9]\.[0-9]{1,2})\s*(?:/\s*10(?:\.0)?)?',
        r'\b([0-9]\.[0-9]{1,2})\s*/\s*10(?:\.0)?\b',
        r'(?:CGPA|GPA)\s*[:=]?\s*([0-9]{1,2}\.[0-9]{1,2})',
    ]
    for pat in cgpa_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if 4.0 <= val <= 10.0:
                    extracted["cgpa"] = val
                    extracted["detected_fields"].append("CGPA")
                    break
                elif val <= 4.0:
                    # Convert 4.0 scale to 10-point scale equivalent (linear scaling * 2.5)
                    extracted["cgpa"] = round(val * 2.5, 2)
                    extracted["detected_fields"].append("CGPA (converted from 4.0)")
                    break
            except ValueError:
                pass

    # 2. GRE Scores
    gre_quant_pat = [
        r'(?:Quantitative\s+Reasoning|Quantitative|Quant)\s*[:=]?\s*([1][3-7][0-9])',
        r'GRE.*?Quantitative\s*[:=]?\s*([1][3-7][0-9])',
    ]
    for pat in gre_quant_pat:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            extracted["gre_quant_scaled"] = int(m.group(1))
            extracted["detected_fields"].append("GRE Quant Scaled")
            break

    # Quant percentile
    quant_pct_pat = r'(?:Quantitative|Quant).*?([0-9]{1,2})\s*%\s*(?:percentile|pct)'
    m_pct = re.search(quant_pct_pat, text, re.IGNORECASE)
    if m_pct:
        extracted["gre_quant_percentile"] = int(m_pct.group(1))
        extracted["detected_fields"].append("GRE Quant Percentile")

    # Verbal percentile
    verbal_pct_pat = r'(?:Verbal).*?([0-9]{1,2})\s*%\s*(?:percentile|pct)'
    m_vpct = re.search(verbal_pct_pat, text, re.IGNORECASE)
    if m_vpct:
        extracted["gre_verbal_percentile"] = int(m_vpct.group(1))
        extracted["detected_fields"].append("GRE Verbal Percentile")

    # Analytical writing
    awa_pat = r'(?:Analytical\s+Writing|AWA)\s*[:=]?\s*([0-6]\.[05])'
    m_awa = re.search(awa_pat, text, re.IGNORECASE)
    if m_awa:
        extracted["gre_awa"] = float(m_awa.group(1))
        extracted["detected_fields"].append("GRE AWA")

    # 3. English Proficiency Tests
    ielts_pat = r'IELTS\s*(?:Academic)?.*?(?:Overall\s+Band\s+Score|Overall|Band)\s*[:=]?\s*([4-9](?:\.[05])?)'
    m_ielts = re.search(ielts_pat, text, re.IGNORECASE)
    if m_ielts:
        extracted["english_test_type"] = "IELTS"
        extracted["english_score"] = float(m_ielts.group(1))
        extracted["detected_fields"].append("IELTS Score")
    else:
        toefl_pat = r'TOEFL\s*(?:iBT)?.*?(?:Total\s+Score|Total|Score)\s*[:=]?\s*([0-9]{2,3})'
        m_toefl = re.search(toefl_pat, text, re.IGNORECASE)
        if m_toefl:
            extracted["english_test_type"] = "TOEFL"
            extracted["english_score"] = float(m_toefl.group(1))
            extracted["detected_fields"].append("TOEFL iBT Score")

    # 4. GATE Exam
    if re.search(r'\bGATE\b.*?(?:Computer\s+Science|CS|Score|Rank)', text, re.IGNORECASE):
        extracted["gate_score_reported"] = True
        extracted["detected_fields"].append("GATE CS Reported")

    # 5. Nationality & Country Mentions
    country_mentions = {
        "India": r'\b(?:India|Indian|New\s+Delhi|Mumbai|Bangalore|Chennai)\b',
        "China": r'\b(?:China|Chinese|Beijing|Shanghai)\b',
        "Germany": r'\b(?:Germany|German|Deutschland|Berlin|Munich|Aachen)\b',
        "United States": r'\b(?:United\s+States|USA|U\.S\.A\.)\b',
        "South Korea": r'\b(?:Korea|Korean|Seoul|Daejeon)\b',
    }
    for c_name, c_pat in country_mentions.items():
        if re.search(c_pat, text, re.IGNORECASE):
            if not extracted["undergrad_country"]:
                extracted["undergrad_country"] = c_name
                extracted["citizenship"] = c_name
                extracted["detected_fields"].append(f"Country/Citizenship: {c_name}")
                break

    # English medium indicator
    if re.search(r'medium\s+of\s+instruction\s*(?:is|was)?\s*English', text, re.IGNORECASE):
        extracted["undergrad_institution_english_medium"] = True
        extracted["detected_fields"].append("English Medium Instruction")

    return extracted
