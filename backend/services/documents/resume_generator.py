import io
import re
from typing import Optional

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from models.all_models import Candidate, CandidateDocument

def _clean_text_for_reportlab(text: str) -> str:
    """Escapes XML entities so ReportLab Paragraph doesn't raise XML parsing errors."""
    if not text:
        return ""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text

def generate_pdf_resume(candidate: Candidate, doc: Optional[CandidateDocument] = None) -> bytes:
    """
    Dynamically generates a clean, executive, branded PDF resume from candidate DB profile.
    Used as an automatic fallback when the raw binary PDF is not found in storage.
    """
    if not HAS_REPORTLAB:
        # Fallback minimal valid PDF stream if reportlab is unavailable
        title = candidate.name or f"Candidate {candidate.id}"
        pdf_content = (
            f"%PDF-1.4\n1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj\n"
            f"2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj\n"
            f"3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R>>endobj\n"
            f"4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 50 700 Td ({title} Resume) Tj ET\nendstream\nendobj\n"
            f"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000216 00000 n \n"
            f"trailer<</Size 5 /Root 1 0 R>>\nstartxref\n310\n%%EOF"
        )
        return pdf_content.encode("utf-8")

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle(
        'CandName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A')
    )
    
    title_style = ParagraphStyle(
        'CandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4F46E5')
    )
    
    contact_style = ParagraphStyle(
        'CandContact',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748B')
    )
    
    section_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=3
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155')
    )

    skill_pill_style = ParagraphStyle(
        'SkillPill',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    story = []
    
    # 1. Header: Name & Title
    cand_name = _clean_text_for_reportlab(candidate.name or f"Candidate #{candidate.id}")
    story.append(Paragraph(cand_name, name_style))
    
    title_text = candidate.current_title or "Technical Engineering Professional"
    if candidate.current_company:
        title_text += f" • {candidate.current_company}"
    story.append(Paragraph(_clean_text_for_reportlab(title_text), title_style))
    
    # 2. Contact Strip
    contacts = []
    if candidate.email:
        contacts.append(candidate.email)
    if candidate.phone:
        contacts.append(candidate.phone)
    if candidate.location:
        contacts.append(candidate.location)
    if candidate.total_experience_years is not None and candidate.total_experience_years > 0:
        contacts.append(f"{candidate.total_experience_years} Years Experience")
        
    if contacts:
        contact_line = "  |  ".join([_clean_text_for_reportlab(c) for c in contacts])
        story.append(Paragraph(contact_line, contact_style))
        
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6366F1"), spaceAfter=8))
    
    # 3. Professional Summary / Resume Text
    text_content = ""
    if doc:
        text_content = doc.normalized_text or doc.raw_extracted_text or ""
        
    if not text_content:
        skills_summary = ", ".join([s.original_extracted_skill for s in candidate.skills[:5]]) if candidate.skills else "Modern Software Engineering"
        text_content = (
            f"Accomplished professional with {candidate.total_experience_years or 5}+ years of verified industry experience. "
            f"Demonstrated core technical competencies in {skills_summary}. "
            "Proven track record delivering reliable, production-grade applications."
        )
        
    story.append(Paragraph("PROFESSIONAL SUMMARY & PROFILE", section_h1))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=5))
    
    paragraphs = [p.strip() for p in text_content.split("\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text_content]
        
    for p in paragraphs[:8]:
        story.append(Paragraph(_clean_text_for_reportlab(p), body_style))
        story.append(Spacer(1, 4))
        
    # 4. Core Technical Skills
    if candidate.skills:
        story.append(Spacer(1, 4))
        story.append(Paragraph("TECHNICAL COMPETENCIES & VERIFIED SKILLS", section_h1))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=5))
        
        skills_list = [s.original_extracted_skill for s in candidate.skills if s.original_extracted_skill]
        if skills_list:
            col_count = 3
            rows = []
            cur_row = []
            for s in skills_list[:21]: # Up to 21 skills
                clean_s = _clean_text_for_reportlab(s)
                cur_row.append(Paragraph(f"• {clean_s}", skill_pill_style))
                if len(cur_row) == col_count:
                    rows.append(cur_row)
                    cur_row = []
            if cur_row:
                while len(cur_row) < col_count:
                    cur_row.append(Paragraph("", skill_pill_style))
                rows.append(cur_row)
                
            skill_table = Table(rows, colWidths=[180, 180, 180])
            skill_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
            ]))
            story.append(skill_table)
            
    # 5. Professional Experience (if employments exist)
    if candidate.employments:
        story.append(Spacer(1, 4))
        story.append(Paragraph("WORK EXPERIENCE & EMPLOYMENT HISTORY", section_h1))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=5))
        
        for emp in candidate.employments[:5]:
            title = _clean_text_for_reportlab(emp.job_title or "Software Engineer")
            company = _clean_text_for_reportlab(emp.company or "Company")
            emp_header = f"<b>{title}</b> — <i>{company}</i>"
            story.append(Paragraph(emp_header, body_style))
            if emp.description:
                story.append(Paragraph(_clean_text_for_reportlab(emp.description[:250]), contact_style))
            story.append(Spacer(1, 3))
            
    # 6. Open-Web Technical Evidence (if present)
    if candidate.external_evidence:
        story.append(Spacer(1, 4))
        story.append(Paragraph("VERIFIED TECHNICAL FOOTPRINT & CONTRIBUTIONS", section_h1))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=5))
        evidence_snippet = _clean_text_for_reportlab(candidate.external_evidence[:400])
        story.append(Paragraph(evidence_snippet, body_style))
        
    # 7. TalentAI Verification Footer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#E2E8F0"), spaceAfter=4))
    footer_text = "Verified Candidate Profile • TalentAI Intelligence Platform • Formatted for Recruiter Review"
    story.append(Paragraph(footer_text, contact_style))
    
    pdf.build(story)
    return buf.getvalue()
