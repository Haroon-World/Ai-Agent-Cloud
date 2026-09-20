"""
ClinicConnect AI — Evaluation Documentation Generator
Generates a professional MS Word (.docx) document for academic submission.
Usage: python scripts/generate_evaluation_doc.py
"""

import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ── Color Palette ──────────────────────────────────────────────────────────────
NAVY        = RGBColor(0x1E, 0x3A, 0x5F)   # Dark navy — headings
DARK_BLUE   = RGBColor(0x1E, 0x40, 0xAF)   # Royal blue — table headers
LIGHT_BLUE  = RGBColor(0xDB, 0xEA, 0xFE)   # Pale blue — alt table rows
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)
DARK_GRAY   = RGBColor(0x1F, 0x2D, 0x3D)
MID_GRAY    = RGBColor(0x64, 0x74, 0x8B)
LIGHT_GRAY  = RGBColor(0xF1, 0xF5, 0xF9)
AMBER       = RGBColor(0xD9, 0x77, 0x06)
GREEN_DARK  = RGBColor(0x16, 0x6B, 0x34)

# ── Helpers ────────────────────────────────────────────────────────────────────

def set_cell_bg(cell, hex_color: str):
    """Set table cell background color."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)


def add_horizontal_rule(doc):
    """Insert a thin horizontal rule paragraph."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '1E3A5F')
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def add_page_break(doc):
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_break(docx_break_type_page())
    return p


def docx_break_type_page():
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    br = OxmlElement('w:br')
    br.set(qn('w:type'), 'page')
    return br


def add_page_number(paragraph):
    """Add 'Page X of Y' to a paragraph."""
    run = paragraph.add_run('Page ')
    fld_begin = OxmlElement('w:fldChar')
    fld_begin.set(qn('w:fldCharType'), 'begin')
    run._r.append(fld_begin)

    instr = OxmlElement('w:instrText')
    instr.set(qn('xml:space'), 'preserve')
    instr.text = 'PAGE'
    run._r.append(instr)

    fld_end = OxmlElement('w:fldChar')
    fld_end.set(qn('w:fldCharType'), 'end')
    run._r.append(fld_end)

    run2 = paragraph.add_run(' of ')

    run3 = paragraph.add_run('')
    fld_begin2 = OxmlElement('w:fldChar')
    fld_begin2.set(qn('w:fldCharType'), 'begin')
    run3._r.append(fld_begin2)

    instr2 = OxmlElement('w:instrText')
    instr2.set(qn('xml:space'), 'preserve')
    instr2.text = 'NUMPAGES'
    run3._r.append(instr2)

    fld_end2 = OxmlElement('w:fldChar')
    fld_end2.set(qn('w:fldCharType'), 'end')
    run3._r.append(fld_end2)


def set_col_width(table, col_idx, width_inches):
    for row in table.rows:
        row.cells[col_idx].width = Inches(width_inches)


def styled_heading(doc, text, level, color=None):
    """Add a heading with custom navy color."""
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    for run in h.runs:
        run.font.color.rgb = color or NAVY
    return h


def body_para(doc, text='', bold=False, color=None, italic=False, size=11, space_before=0, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = Pt(size)
        if color:
            run.font.color.rgb = color
    return p


def bullet_item(doc, text, level=0, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Inches(0.25 + level * 0.25)
    if bold_prefix:
        run_b = p.add_run(bold_prefix)
        run_b.bold = True
        run_b.font.size = Pt(11)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p


def numbered_item(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Number')
    p.paragraph_format.space_after = Pt(3)
    if bold_prefix:
        run_b = p.add_run(bold_prefix)
        run_b.bold = True
        run_b.font.size = Pt(11)
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p


def figure_placeholder(doc, fig_num, title, description):
    """Create a visually bordered image placeholder box."""
    # Shaded paragraph as box
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'DBEAFE')
    pPr.append(shd)
    # Border around paragraph
    pBdr = OxmlElement('w:pBdr')
    for side in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{side}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '12')
        el.set(qn('w:space'), '4')
        el.set(qn('w:color'), '1E40AF')
        pBdr.append(el)
    pPr.append(pBdr)

    run1 = p.add_run(f'  📷  Figure {fig_num}:  {title}')
    run1.bold = True
    run1.font.size = Pt(11)
    run1.font.color.rgb = DARK_BLUE

    p2 = doc.add_paragraph()
    p2.paragraph_format.left_indent = Inches(0.3)
    p2.paragraph_format.space_before = Pt(0)
    p2.paragraph_format.space_after = Pt(4)
    r2 = p2.add_run(f'     [ INSERT SCREENSHOT HERE ]     —  {description}')
    r2.italic = True
    r2.font.size = Pt(10)
    r2.font.color.rgb = MID_GRAY


# ── Document Setup ─────────────────────────────────────────────────────────────

def create_document():
    doc = Document()

    # Page margins: 1 inch all sides
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.15)
        section.right_margin  = Inches(1.15)

    # Default body font
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = Pt(11)
    style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE

    # Override heading styles
    for lvl, sz, bold in [(1, 16, True), (2, 14, True), (3, 12, True)]:
        h_style = doc.styles[f'Heading {lvl}']
        h_style.font.name = 'Calibri'
        h_style.font.size = Pt(sz)
        h_style.font.bold = bold
        h_style.font.color.rgb = NAVY

    return doc


# ── Sections ───────────────────────────────────────────────────────────────────

def cover_page(doc):
    sec = doc.sections[0]

    # Spacer
    for _ in range(5):
        doc.add_paragraph()

    # Institute
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p_inst.add_run('Arfa Karim Technology Incubator')
    r.font.size = Pt(13)
    r.font.color.rgb = MID_GRAY
    r.font.name = 'Calibri'

    doc.add_paragraph()

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run('ClinicConnect AI')
    r_t.font.size = Pt(28)
    r_t.font.bold = True
    r_t.font.color.rgb = NAVY
    r_t.font.name = 'Calibri'

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_s = p_sub.add_run('Autonomous AI Appointment & Clinic Management System')
    r_s.font.size = Pt(15)
    r_s.font.color.rgb = DARK_BLUE
    r_s.font.name = 'Calibri'

    doc.add_paragraph()
    add_horizontal_rule(doc)
    doc.add_paragraph()

    # Meta info table
    meta_table = doc.add_table(rows=5, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ('Project Title',     'ClinicConnect AI – Autonomous Appointment & Clinic Management System'),
        ('Author / Developer','Muhammad Haroon Siddique'),
        ('Role',              'Full-Stack Developer & UI/UX Designer'),
        ('Instructor',        'Sir Rana Zain Idress'),
        ('Institute',         'Arfa Karim Technology Incubator'),
    ]
    for i, (label, value) in enumerate(meta_data):
        row = meta_table.rows[i]
        cell_l = row.cells[0]
        cell_r = row.cells[1]
        cell_l.width = Inches(2.2)
        cell_r.width = Inches(4.0)
        set_cell_bg(cell_l, 'DBEAFE')
        rl = cell_l.paragraphs[0].add_run(label)
        rl.bold = True
        rl.font.size = Pt(11)
        rl.font.name = 'Calibri'
        rl.font.color.rgb = NAVY
        rr = cell_r.paragraphs[0].add_run(value)
        rr.font.size = Pt(11)
        rr.font.name = 'Calibri'

    doc.add_paragraph()

    p_url = doc.add_paragraph()
    p_url.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ru = p_url.add_run('Live at: https://clinic-connect-ai.onrender.com')
    ru.font.size = Pt(11)
    ru.font.color.rgb = DARK_BLUE
    ru.font.name = 'Calibri'

    doc.add_paragraph()

    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rd = p_date.add_run('Submission Date: September 2026')
    rd.font.size = Pt(11)
    rd.font.color.rgb = MID_GRAY
    rd.font.name = 'Calibri'

    # Page break after cover
    doc.add_page_break()


def table_of_contents(doc):
    styled_heading(doc, 'Table of Contents', 1)

    toc_items = [
        ('1.', 'Project Overview'),
        ('2.', 'Features'),
        ('   2.1', 'Patient-Facing Conversational AI Channel'),
        ('   2.2', 'Clinic Admin & Staff Operations Portal'),
        ('   2.3', 'Doctor Multi-Shift Schedule & Slot Management'),
        ('   2.4', 'Manual Booking with Intelligent Conflict Avoidance'),
        ('   2.5', 'Live Conversation Monitoring & Human Handoff'),
        ('   2.6', 'Multi-Tenant Platform Owner Console'),
        ('3.', 'Architecture'),
        ('   3.1', 'High-Level System Architecture'),
        ('   3.2', 'Agentic AI Decision & Booking Pipeline'),
        ('   3.3', 'Multi-Tenant Isolation & Security Model'),
        ('4.', 'Tech Stack'),
        ('5.', 'Live Demo Link'),
        ('6.', 'GitHub Repository & Development History'),
        ('7.', 'Individual Contributions'),
        ('8.', 'Evaluation Visual Exhibit & Screenshots'),
    ]

    for num, title in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r_num = p.add_run(f'{num}  ')
        r_num.bold = True if not num.startswith('  ') else False
        r_num.font.size = Pt(11)
        r_num.font.color.rgb = NAVY
        r_title = p.add_run(title)
        r_title.font.size = Pt(11)
        if not num.startswith('  '):
            r_title.bold = True

    doc.add_page_break()


def section_overview(doc):
    styled_heading(doc, '1. Project Overview', 1)

    body_para(doc, (
        'ClinicConnect AI is a production-ready, multi-tenant Software-as-a-Service (SaaS) platform engineered '
        'to eliminate the operational bottlenecks facing modern medical clinics, polyclinics, dental practices, '
        'and healthcare centers of all scales.'
    ))

    styled_heading(doc, 'Problem Statement', 2)
    body_para(doc, (
        'Traditional outpatient clinics lose up to 30% of incoming booking inquiries due to perpetually busy '
        'reception phone lines, delayed responses after clinic hours, double-booked appointments, and manual '
        'scheduling errors. Front-desk receptionists spend the majority of their shift answering repetitive '
        'intake questions rather than providing in-clinic patient care.'
    ))

    styled_heading(doc, 'The Solution', 2)
    body_para(doc, (
        'ClinicConnect AI deploys an autonomous, conversational AI receptionist across Web Chat and WhatsApp. '
        'The AI engages patients in natural language, queries live doctor practising schedules in real time, '
        'validates slot availability, resolves scheduling conflicts, registers patient credentials, and commits '
        'appointments atomically into the relational database. Concurrently, clinic administrators and medical '
        'staff access a centralized SaaS portal to manage doctor weekly schedules, monitor live chat sessions, '
        'execute Human-in-the-Loop (HITL) takeovers, and process walk-in or telephone bookings.'
    ))

    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_features(doc):
    styled_heading(doc, '2. Features', 1)

    features = [
        ('2.1  Patient-Facing Conversational AI Channel', [
            ('Omnichannel Availability:', ' Operates 24/7 across Web Chat and WhatsApp Cloud API, ensuring patients can always reach the clinic.'),
            ('Natural Language Inquiry:', ' Answers questions about services, procedures, pricing (PKR), and doctor specializations in plain language.'),
            ('Intelligent Slot Discovery:', ' Recommends available appointment slots in 12-hour format (e.g., 09:30 AM, 02:00 PM).'),
            ('Conversational Memory:', ' Preserves multi-turn dialogue context and session state across user intents.'),
            ('Voice Capabilities:', ' Supports Speech-to-Text (STT) voice notes and Text-to-Speech (TTS) audio responses.'),
        ]),
        ('2.2  Clinic Admin & Staff Operations Portal', [
            ('Executive SaaS Dashboard:', ' Real-time KPI telemetry — Total Appointments, Revenue, Active Patients, and Conversion Rate.'),
            ('Recent Activity Feed:', ' Live timeline showing confirmed, scheduled, and completed appointments.'),
            ('Global Topbar Search:', ' Instant keyword lookup across patients, phone numbers, appointment IDs, doctors, and services.'),
            ('12-Hour AM/PM Time Format:', ' Consistent time display across all tables, drawers, and filters — no military time confusion.'),
        ]),
        ('2.3  Doctor Multi-Shift Schedule & Slot Management', [
            ('Split-Shift Support:', ' Independent configuration of Shift 1 (morning) and Shift 2 (evening) per doctor.'),
            ('Lunch Break Protection:', ' Configurable clinic break windows are automatically excluded from patient bookings.'),
            ('1-Click Schedule Presets:', ' Fast preset templates (e.g., 09:00 AM – 05:00 PM) to configure all working days instantly.'),
            ('Blocked Dates & Leave Management:', ' Block entire days or partial hours for doctor conferences, vacations, or on-call duties.'),
            ('Visual Schedule Grid:', ' Scrollable weekly timeline to visually preview physician availability at a glance.'),
        ]),
        ('2.4  Manual Booking with Intelligent Conflict Avoidance', [
            ('Walk-in & Phone Booking Modal:', ' Streamlined reception interface for patients calling or visiting reception directly.'),
            ('Visual Slot Template Grid:', ' Live color-coded pill grid — green for available slots, red for booked or occupied slots.'),
            ('Inline Conflict Alerts (Zero Browser Popups):', ' Selecting an occupied slot immediately triggers a non-intrusive inline warning card.'),
            ('12-Hour Dropdown Selector:', ' Eliminates military-time input errors with pre-populated 15-minute interval options.'),
        ]),
        ('2.5  Live Conversation Monitoring & Human Handoff', [
            ('Split-Screen Conversation Inbox:', ' Real-time monitoring of all active patient AI sessions from a single view.'),
            ('Human-in-the-Loop (HITL) Takeover:', ' Staff can pause the AI receptionist with a single toggle and reply directly to the patient.'),
            ('Lead & Patient Metadata:', ' Displays patient contact details, appointment intent status, and conversation context.'),
        ]),
        ('2.6  Multi-Tenant Platform Owner Console', [
            ('Multi-Clinic Onboarding:', ' Master admin interface to onboard independent clinics with unique domains and credentials.'),
            ('Subscription Lifecycle Management:', ' Tiered plans (Starter, Professional, Enterprise) with automated access control and expiration.'),
            ('Clinic Switcher:', ' Platform admins can switch context between different clinics without re-authenticating.'),
        ]),
    ]

    for heading, bullets in features:
        styled_heading(doc, heading, 2)
        for bold_text, rest in bullets:
            bullet_item(doc, rest, bold_prefix=bold_text)
        doc.add_paragraph()

    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_architecture(doc):
    styled_heading(doc, '3. Architecture', 1)

    styled_heading(doc, '3.1  High-Level System Architecture', 2)
    body_para(doc, (
        'The system is organized into four horizontal tiers, each with a clearly defined responsibility boundary:'
    ))

    arch_layers = [
        ('Patient Client Layer',
         'Web Chat (browser widget) and WhatsApp Mobile (Meta Cloud API) — patient entry points.'),
        ('Gateway & Routing Layer',
         'Flask Application Gateway with modular Blueprints, Tenant & Session Authentication Guard, and '
         'WhatsApp Webhook Signature Verifier (HMAC SHA-256).'),
        ('Agentic Intelligence & Business Logic Layer',
         'AI Receptionist Orchestrator powered by Google Gemini / Groq Llama-3 LLM. The BookingService '
         'performs atomic slot validation and conflict resolution. The ScheduleService computes valid '
         'practising windows from shifts, breaks, and leave rules.'),
        ('Persistence & External Services Layer',
         'PostgreSQL (production) / SQLite (development) relational database with SQLAlchemy ORM. '
         'Celery background task runner dispatches appointment reminders via Meta WhatsApp Cloud Graph API.'),
    ]

    for name, desc in arch_layers:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        r_name = p.add_run(f'► {name}: ')
        r_name.bold = True
        r_name.font.size = Pt(11)
        r_name.font.color.rgb = NAVY
        r_desc = p.add_run(desc)
        r_desc.font.size = Pt(11)

    figure_placeholder(doc, '1.0',
                       'System Architecture Diagram',
                       'High-level layered architecture showing Patient Channels → Flask Gateway → AI Engine → Database')

    styled_heading(doc, '3.2  Agentic AI Decision & Booking Pipeline', 2)
    body_para(doc, (
        'The following sequence describes a complete end-to-end patient interaction from initial message '
        'through to confirmed appointment:'
    ))

    pipeline_steps = [
        'Patient sends a natural-language request via Web Chat or WhatsApp (e.g., "I want an appointment with Dr. Ahmed Khan tomorrow morning").',
        'The AI Receptionist Orchestrator interprets intent and calls check_availability(doctor_id, date, duration) on the BookingService.',
        'BookingService queries the DoctorSchedule table for active shifts, break windows, and leave blocks.',
        'BookingService executes an overlap-filter query against existing appointments to identify truly open slots.',
        'The AI presents available slots in 12-hour format to the patient (e.g., "09:00 AM, 09:30 AM, or 11:00 AM").',
        'The patient selects a time and provides their name and phone number.',
        'BookingService executes an atomic database transaction: re-validates overlap, then inserts the appointment record.',
        'The system returns Appointment ID and confirmation to the AI, which presents a booking confirmation card to the patient.',
        'The new appointment is pushed live to the Clinic Admin Dashboard and Slots Matrix.',
        'Celery triggers a scheduled WhatsApp reminder 24 hours before the appointment.',
    ]

    for step in pipeline_steps:
        p = doc.add_paragraph(style='List Number')
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(step)
        r.font.size = Pt(11)

    figure_placeholder(doc, '1.1',
                       'AI Booking Pipeline Sequence',
                       'Sequence diagram: Patient → AI Orchestrator → BookingService → DB → Confirmation')

    styled_heading(doc, '3.3  Multi-Tenant Isolation & Security Model', 2)
    bullets_sec = [
        ('Tenant Scoping:', ' Every SQL query in the clinic portal is strictly scoped to business_id = session[\'business_id\'], preventing cross-tenant data leakage.'),
        ('Database Partitioning:', ' All appointments, customers, services, doctors, and conversations hold strict foreign key relationships tied to the clinic tenant.'),
        ('Privilege Separation:', ' Platform superadmins (/platform) and clinic staff (/admin) use decoupled authentication middleware, preventing privilege escalation.'),
        ('Atomic Transactions:', ' Appointment insertion uses BEGIN/COMMIT transactions with re-validation, guaranteeing no double-booking under concurrent load.'),
    ]
    for bold_text, rest in bullets_sec:
        bullet_item(doc, rest, bold_prefix=bold_text)

    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_tech_stack(doc):
    styled_heading(doc, '4. Tech Stack', 1)

    body_para(doc, 'The following technologies were selected to balance developer velocity, production reliability, and healthcare-grade data integrity:')
    doc.add_paragraph()

    headers = ['Domain', 'Technology', 'Role & Justification']
    rows = [
        ('Backend Framework',       'Python 3.12, Flask',                        'Lightweight, rapid request handling; modular Blueprints architecture for multi-tenant routing.'),
        ('Database & ORM',          'PostgreSQL / SQLite, SQLAlchemy',           'ACID-compliant relational persistence, foreign-key multi-tenant isolation, and atomic transactions.'),
        ('AI / LLM Engine',         'Google Gemini 2.5 / Groq Llama-3',         'High-speed semantic comprehension, zero-shot entity extraction, and tool-calling function interfaces.'),
        ('Messaging Channel',        'Meta WhatsApp Cloud API',                  'Official Meta Graph API webhooks for scalable, verified WhatsApp patient communication.'),
        ('Voice Processing',         'OpenAI Whisper (STT) + ElevenLabs / Edge-TTS', 'Multilingual audio transcription and speech synthesis for accessibility and voice-channel support.'),
        ('Frontend Architecture',    'HTML5, CSS3, JavaScript ES6+, Jinja2',     'High-performance custom SaaS interface — zero framework bloat, sub-50ms page loads.'),
        ('Typography & Design',      'Plus Jakarta Sans, FontAwesome SVG Icons', 'Modern, premium SaaS aesthetics optimized for medical administrative portals.'),
        ('Testing Framework',        'Pytest, Unittest',                         'Comprehensive unit, integration, and regression test suites — 57 automated tests, 100% passing.'),
        ('Deployment / PaaS',        'Render, Gunicorn, Git',                    'Production cloud deployment with environment variable isolation and automatic SSL certificate.'),
        ('Background Tasks',         'Celery + Redis / APScheduler',             'Asynchronous appointment reminders dispatched via WhatsApp at configurable intervals.'),
    ]

    table = doc.add_table(rows=len(rows) + 1, cols=3)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    hdr_cells = table.rows[0].cells
    for i, hdr in enumerate(headers):
        set_cell_bg(hdr_cells[i], '1E40AF')
        p = hdr_cells[i].paragraphs[0]
        r = p.add_run(hdr)
        r.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(11)
        r.font.name = 'Calibri'
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Data rows
    for row_idx, (domain, tech, role) in enumerate(rows):
        row = table.rows[row_idx + 1]
        bg = 'DBEAFE' if row_idx % 2 == 0 else 'FFFFFF'
        for ci, text in enumerate((domain, tech, role)):
            set_cell_bg(row.cells[ci], bg)
            p = row.cells[ci].paragraphs[0]
            r = p.add_run(text)
            r.font.size = Pt(10.5)
            r.font.name = 'Calibri'
            if ci == 0:
                r.bold = True
                r.font.color.rgb = NAVY

    # Column widths
    for row in table.rows:
        row.cells[0].width = Inches(1.7)
        row.cells[1].width = Inches(2.2)
        row.cells[2].width = Inches(3.3)

    doc.add_paragraph()
    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_live_demo(doc):
    styled_heading(doc, '5. Live Demo Link', 1)

    body_para(doc, 'The application is deployed on Render PaaS and is publicly accessible at the following URLs:')
    doc.add_paragraph()

    demo_table = doc.add_table(rows=4, cols=2)
    demo_table.style = 'Table Grid'

    demo_links = [
        ('Main Web Application',     'https://clinic-connect-ai.onrender.com'),
        ('Patient AI Web Chat',       'https://clinic-connect-ai.onrender.com/chat'),
        ('Clinic Admin Portal',       'https://clinic-connect-ai.onrender.com/admin/login'),
        ('Platform Superadmin',       'https://clinic-connect-ai.onrender.com/platform/login'),
    ]

    hdr_row = demo_table.rows[0]
    for ci, txt in enumerate(('Portal', 'URL')):
        set_cell_bg(hdr_row.cells[ci], '1E40AF')
        r = hdr_row.cells[ci].paragraphs[0].add_run(txt)
        r.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(11)

    for i, (label, url) in enumerate(demo_links):
        row = demo_table.rows[i]
        set_cell_bg(row.cells[0], 'DBEAFE' if i % 2 == 0 else 'FFFFFF')
        r_l = row.cells[0].paragraphs[0].add_run(label)
        r_l.bold = True
        r_l.font.size = Pt(11)
        r_l.font.color.rgb = NAVY
        r_u = row.cells[1].paragraphs[0].add_run(url)
        r_u.font.size = Pt(11)
        r_u.font.color.rgb = DARK_BLUE

    doc.add_paragraph()
    styled_heading(doc, 'Evaluator Access Credentials', 2)

    creds_table = doc.add_table(rows=3, cols=3)
    creds_table.style = 'Table Grid'

    creds_hdr = creds_table.rows[0]
    for ci, txt in enumerate(('Portal', 'Username', 'Password')):
        set_cell_bg(creds_hdr.cells[ci], '1E3A5F')
        r = creds_hdr.cells[ci].paragraphs[0].add_run(txt)
        r.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(11)

    creds_data = [
        ('Clinic Admin Portal',    'admin',                'admin123'),
        ('Platform Superadmin',    'clinicconnectaipro',   '@Clinic2026'),
    ]
    for i, (portal, user, pwd) in enumerate(creds_data):
        row = creds_table.rows[i + 1]
        set_cell_bg(row.cells[0], 'DBEAFE' if i % 2 == 0 else 'FFFFFF')
        for ci, txt in enumerate((portal, user, pwd)):
            r = row.cells[ci].paragraphs[0].add_run(txt)
            r.font.size = Pt(11)
            if ci == 2:
                r.font.name = 'Courier New'
                r.font.color.rgb = GREEN_DARK

    doc.add_paragraph()
    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_github(doc):
    styled_heading(doc, '6. GitHub Repository & Development History', 1)

    styled_heading(doc, 'Official Deployment Repository', 2)
    body_para(doc, 'Repository (Active / Deployment):  https://github.com/Haroon-World/Ai-Agent-Cloud', bold=False)
    body_para(doc, 'Branch: main  |  License: MIT License')

    styled_heading(doc, 'Development History', 2)
    body_para(doc, (
        'The project was initially developed in a separate repository and later moved/cloned into the '
        'deployment repository used for the final Render deployment. The original development repository '
        'is preserved at:'
    ))
    body_para(doc, '  Original Repository:   https://github.com/Haroon-World/Ai-Agent')
    body_para(doc, '  Deployment Repository: https://github.com/Haroon-World/Ai-Agent-Cloud')
    body_para(doc, (
        'The transition was made to enable clean Render deployment configuration, environment variable '
        'management, and separation of development history from the production-ready codebase. All core '
        'intellectual contributions and architectural work originate from the original repository.'
    ))

    add_horizontal_rule(doc)
    doc.add_paragraph()


def section_contributions(doc):
    styled_heading(doc, '7. Individual Contributions', 1)

    styled_heading(doc, '7.1  Full-Stack Developer & UI/UX Designer', 2)

    p_name = doc.add_paragraph()
    p_name.paragraph_format.space_after = Pt(4)
    r_label = p_name.add_run('Contributor: ')
    r_label.bold = True
    r_label.font.size = Pt(11)
    r_val = p_name.add_run('Muhammad Haroon Siddique')
    r_val.font.size = Pt(11)
    r_val.font.color.rgb = NAVY

    p_role = doc.add_paragraph()
    p_role.paragraph_format.space_after = Pt(8)
    r_rl = p_role.add_run('Role: ')
    r_rl.bold = True
    r_rl.font.size = Pt(11)
    r_rv = p_role.add_run('Full-Stack Software Architect, AI Pipeline Engineer, Database Engineer, UI/UX System Designer')
    r_rv.font.size = Pt(11)

    contrib_sections = [
        ('Multi-Tenant SaaS Backend Architecture', [
            'Designed and implemented modular Flask Blueprint routing architecture (admin, platform, api, auth modules).',
            'Engineered tenant-scoping middleware ensuring 100% row-level data isolation between independent clinic tenants.',
            'Built atomic transaction booking pipelines in BookingService with slot overlap validation and conflict resolution.',
            'Implemented session-based authentication with multi-role privilege separation (clinic staff vs platform superadmin).',
        ]),
        ('Agentic Conversational AI Pipeline', [
            'Designed the AI Receptionist prompt hierarchy, intent classification, and multi-turn state machine.',
            'Integrated Google Gemini and Groq Llama-3 LLMs with structured tool calling for real-time slot availability.',
            'Implemented WhatsApp Cloud API webhook ingestion with HMAC SHA-256 message signature verification.',
            'Engineered Celery-based background reminders dispatching WhatsApp notifications 24 hours before appointments.',
        ]),
        ('Time Standardization & 12-Hour AM/PM Engine', [
            'Created the format_12hr Jinja2 template filter converting backend HH:MM military time to 12-hour AM/PM strings.',
            'Engineered bidirectional time normalization — normalize_time_to_24h() ensures database integrity while format_time_to_12h() drives user-facing displays.',
            'Applied standardized time format across all admin templates: dashboard, appointments, reminders, slots, and doctor schedules.',
        ]),
        ('UI/UX System Design', [
            'Crafted the complete SaaS design system: Plus Jakarta Sans typography, high-contrast status badges, CSS flex/grid layout architecture.',
            'Designed the Doctor Schedule Matrix with interactive weekly day cards showing Shift 1, Shift 2, lunch breaks, and leave blocks.',
            'Designed the Visual Slot Template Grid — green available pills and red occupied pills — replacing browser popups with inline conflict alert cards.',
            'Built the real-time split-screen Conversation Inbox with Human-in-the-Loop (HITL) staff takeover controls.',
            'Implemented global topbar search with instant keyword filtering across all admin entities.',
        ]),
    ]

    for section_title, points in contrib_sections:
        styled_heading(doc, section_title, 3)
        for point in points:
            bullet_item(doc, point)
        doc.add_paragraph()

    add_horizontal_rule(doc)

    styled_heading(doc, '7.2  Quality Assurance (QA) & Test Engineer', 2)

    p_name2 = doc.add_paragraph()
    r_label2 = p_name2.add_run('Contributor: ')
    r_label2.bold = True
    r_label2.font.size = Pt(11)
    r_val2 = p_name2.add_run('[Teammate Name]')
    r_val2.font.size = Pt(11)
    r_val2.font.color.rgb = MID_GRAY
    r_val2.italic = True

    p_role2 = doc.add_paragraph()
    p_role2.paragraph_format.space_after = Pt(8)
    r_rl2 = p_role2.add_run('Role: ')
    r_rl2.bold = True
    r_rl2.font.size = Pt(11)
    r_rv2 = p_role2.add_run('Quality Assurance, Test Automation, Edge-Case Auditing, and Manual Verification')
    r_rv2.font.size = Pt(11)

    qa_sections = [
        ('Automated Test Suite Design & Execution', [
            'Developed and maintained 57 automated test cases across 5 distinct test suites — achieving a 100% pass rate.',
            'test_12hr_time_and_manual_booking.py: Validated 12-hour time normalization, slot generation APIs, and HTTP 409 conflict detection on double bookings.',
            'test_multitenant_auth.py: Audited session isolation, cross-tenant data access prevention, and authentication boundary enforcement (30 test cases).',
            'test_doctor_schedules.py: Verified multi-shift calculations, lunch break exclusion logic, and day-off boundary conditions.',
            'test_polyclinic_flow_and_admin_fixes.py: End-to-end appointment booking, status transitions, and cancellation lifecycle (14 test cases).',
            'test_topbar_search_and_dashboard_date.py: Tested global search filtering across doctors, patients, appointment IDs, and services.',
        ]),
        ('Manual Exploratory & Stress Testing', [
            'Tested high-concurrency appointment submissions to confirm atomic database constraints prevent double-booking.',
            'Validated cross-browser UI responsiveness across Google Chrome, Mozilla Firefox, Microsoft Edge, and mobile Safari.',
            'Performed adversarial edge-case testing: past-date bookings, invalid phone formats, missing patient names, and rapid multi-click form submissions.',
            'Verified WhatsApp webhook payload handling under malformed and duplicate message scenarios.',
        ]),
    ]

    for section_title, points in qa_sections:
        styled_heading(doc, section_title, 3)
        for point in points:
            bullet_item(doc, point)
        doc.add_paragraph()

    add_horizontal_rule(doc)
    doc.add_paragraph()


def add_real_figure(doc, fig_num, title, description, image_path, width_inches=6.0):
    """Add a labelled figure with a real embedded image and caption."""
    p_label = doc.add_paragraph()
    p_label.paragraph_format.space_before = Pt(10)
    p_label.paragraph_format.space_after = Pt(4)
    rl = p_label.add_run(f'Figure {fig_num}  --  {title}')
    rl.bold = True
    rl.font.size = Pt(11)
    rl.font.color.rgb = NAVY

    try:
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_after = Pt(4)
        run = p_img.add_run()
        run.add_picture(image_path, width=Inches(width_inches))
    except Exception as e:
        figure_placeholder(doc, fig_num, title, f'[Image could not be embedded: {e}]')
        return

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(8)
    rc = p_cap.add_run(description)
    rc.italic = True
    rc.font.size = Pt(9.5)
    rc.font.color.rgb = MID_GRAY


def section_screenshots(doc):
    styled_heading(doc, '8. Evaluation Visual Exhibit & Screenshots', 1)

    body_para(doc, (
        'The following figures showcase the key interfaces and features of ClinicConnect AI, '
        'captured from the live deployed application at https://clinic-connect-ai.onrender.com'
    ))
    doc.add_paragraph()

    IMG_DIR = r'C:\Users\hanii\.gemini\antigravity\brain\a7606644-5259-4e81-accf-2dbbf728abb5\.user_uploaded'

    add_real_figure(
        doc,
        fig_num='1.0',
        title='Patient AI Webchat -- End-to-End Booking Flow',
        description=(
            'The AI Receptionist guides the patient through the full booking sequence: '
            'doctor selection -> service selection -> slot confirmation -> name & phone capture -> confirmed appointment card. '
            'Note the 12-hour AM/PM time format and natural conversational tone.'
        ),
        image_path=os.path.join(IMG_DIR, 'media_1789906988856.png'),
        width_inches=5.8,
    )
    doc.add_paragraph()

    add_real_figure(
        doc,
        fig_num='2.0',
        title='Clinic Admin Dashboard -- Real-Time KPI & Activity Feed',
        description=(
            'Executive dashboard showing live KPI cards (Today\'s Appointments, AI Conversations, '
            'Appointments Booked by AI, Human Handoff Requests), upcoming appointments table with status badges, '
            'and AI Receptionist Activity feed — all scoped to the logged-in clinic tenant.'
        ),
        image_path=os.path.join(IMG_DIR, 'media_1789906988861.png'),
        width_inches=6.0,
    )
    doc.add_paragraph()

    add_real_figure(
        doc,
        fig_num='3.0',
        title='Doctor Multi-Shift Schedule Configuration Modal',
        description=(
            'Edit Doctor modal showing Per-Day Working Hours configuration with Quick Preset buttons, '
            'Lunch Break Range input, and individual day checkboxes with Shift 1 / + Add Shift 2 time pickers.'
        ),
        image_path=os.path.join(IMG_DIR, 'media_1789906988865.png'),
        width_inches=5.5,
    )
    doc.add_paragraph()

    add_real_figure(
        doc,
        fig_num='4.0',
        title='Doctor Slot Occupancy -- Visual Slot Matrix & Manual Booking',
        description=(
            'Slot occupancy view showing overall clinic utilization gauge (40%), per-doctor slot cards '
            '(red = BOOKED with patient name, green = AVAILABLE with click-to-book), and utilization progress bar.'
        ),
        image_path=os.path.join(IMG_DIR, 'media_1789906988896.png'),
        width_inches=6.0,
    )
    doc.add_paragraph()

    figure_placeholder(
        doc, '5.0',
        'Live Patient Conversations & Human-in-the-Loop (HITL) Handoff',
        'Conversations inbox -- left sidebar with active chats, right panel with transcript, patient metadata, and HITL takeover toggle.'
    )
    doc.add_paragraph()

    figure_placeholder(
        doc, '6.0',
        'Platform Superadmin Console & Multi-Clinic Management',
        'Platform dashboard -- onboarded clinic list, subscription tiers, domain slugs, and system health.'
    )
    doc.add_paragraph()

    add_real_figure(
        doc,
        fig_num='7.0',
        title='Automated Test Suite -- 57/57 Tests Passing',
        description=(
            'Pytest terminal output confirming 57 automated tests across 5 test suites all pass with 0 failures. '
            'Covers 12-hour time normalization, booking conflict detection, multi-tenant auth, polyclinic flow, and doctor schedules.'
        ),
        image_path=os.path.join(IMG_DIR, 'media_1789906988855.png'),
        width_inches=5.5,
    )
    doc.add_paragraph()

    add_horizontal_rule(doc)

    doc.add_paragraph()
    p_footer = doc.add_paragraph()
    p_footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_f = p_footer.add_run('Submitted for Academic Project Evaluation -- Arfa Karim Technology Incubator -- 2026')
    r_f.font.size = Pt(10)
    r_f.font.color.rgb = MID_GRAY
    r_f.italic = True


# ── Header & Footer ────────────────────────────────────────────────────────────

def add_header_footer(doc):
    """Add running header and page-number footer to all non-cover sections."""
    # We need a separate section for cover (no header/footer) vs rest
    # Since we added a page break after cover, we work with sections[0] only
    # For simplicity, add header/footer that will appear on all pages
    # (standard for academic docs — cover page number is usually suppressed manually)
    for i, section in enumerate(doc.sections):
        # Header
        header = section.header
        header.is_linked_to_previous = False
        h_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        h_para.clear()
        h_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_h = h_para.add_run('ClinicConnect AI  |  Project Evaluation Report  |  Muhammad Haroon Siddique')
        r_h.font.size = Pt(9)
        r_h.font.color.rgb = MID_GRAY
        r_h.font.name = 'Calibri'

        # Thin bottom border on header paragraph
        pPr = h_para._p.get_or_add_pPr()
        pBdr = OxmlElement('w:pBdr')
        bottom = OxmlElement('w:bottom')
        bottom.set(qn('w:val'), 'single')
        bottom.set(qn('w:sz'), '4')
        bottom.set(qn('w:space'), '1')
        bottom.set(qn('w:color'), '94A3B8')
        pBdr.append(bottom)
        pPr.append(pBdr)

        # Footer
        footer = section.footer
        footer.is_linked_to_previous = False
        f_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        f_para.clear()
        f_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_page_number(f_para)
        for run in f_para.runs:
            run.font.size = Pt(9)
            run.font.color.rgb = MID_GRAY
            run.font.name = 'Calibri'


# ── Section 9: AI Prompt Design ───────────────────────────────────────────────

def section_ai_prompt_design(doc):
    styled_heading(doc, '9. AI Prompt Design', 1)

    body_para(doc, (
        'The AI Receptionist is driven by a dynamically constructed system prompt — rebuilt on every conversation '
        'turn using live clinic data fetched directly from the database. This ensures the AI always reasons from '
        'up-to-date doctor schedules, services, and pricing rather than from stale hardcoded knowledge.'
    ))

    styled_heading(doc, '9.1  Prompt Architecture', 2)
    body_para(doc, (
        'The system prompt is assembled in ai/prompts.py by the build_system_prompt(business_id) function. '
        'It is structured into four major blocks:'
    ))

    blocks = [
        ('Block 1 — Clinic Identity & Live Context',
         'Injects the clinic name, address, phone, timezone, operating hours, policies, and consultation fee '
         'dynamically from the Business database record. The current local time in the clinic\'s timezone is '
         'computed and embedded so the AI can make accurate "today / tomorrow / this Saturday" date decisions.'),
        ('Block 2 — Doctors & Weekly Schedules',
         'Fetches all active doctors for the clinic including their per-day weekly schedule (DoctorSchedule), '
         'break windows, slot intervals, and Shift 1 / Shift 2 hours. Results are cached per request cycle '
         '(RequestCache) to avoid redundant database queries within the same conversation turn.'),
        ('Block 3 — Services & Pricing by Doctor',
         'Fetches active services grouped per doctor with names, durations, and PKR prices. Services are '
         'strictly associated per doctor — the AI is explicitly prohibited from cross-suggesting a service '
         'that belongs to a different specialist.'),
        ('Block 4 — Behavioral Rules & Guardrails (14 numbered directives)',
         'A comprehensive set of 14 explicit behavioral rules governing the AI\'s conversation flow, '
         'safety constraints, and edge-case handling. Key rules include:'),
    ]

    for name, desc in blocks:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        rn = p.add_run(f'  {name}:  ')
        rn.bold = True
        rn.font.size = Pt(11)
        rn.font.color.rgb = NAVY
        rd = p.add_run(desc)
        rd.font.size = Pt(11)

    rules = [
        ('Sequential Booking Workflow:', 'Doctor → Service → Date → Availability Check → Time → Patient Name & Phone → Confirm & Book. The AI cannot skip steps.'),
        ('Polyclinic Doctor-First Rule:', 'The AI NEVER shows a flat combined service list. It must route the patient to a specific doctor first, then show only that doctor\'s services.'),
        ('Redundant Tool Call Prevention:', 'The AI avoids re-calling get_doctors or get_services if those are already known from context.'),
        ('Multi-Doctor Availability Guard:', 'The AI never calls check_availability without a confirmed doctor_id. It asks the patient to select a doctor first.'),
        ('Negation & Context Understanding:', 'The AI detects negation ("cancel mat karna" = do NOT cancel). It never treats a question number as a requested booking slot.'),
        ('Inviolable Booking Gate:', 'book_appointment is NEVER called unless the patient explicitly confirmed their selection. Questions are never treated as confirmations.'),
        ('Patient Name Integrity:', 'Only a genuine human name is accepted. Fee questions, symptoms, or banter are never treated as patient names.'),
        ('Multilingual Support:', 'English, Urdu script, and Roman Urdu are all understood and replied to in the same language the patient used — with a strict language-lock rule preventing unwanted language switching.'),
        ('Human Handoff:', 'If the patient asks to speak to a human, the AI immediately calls human_handoff without argument.'),
        ('Live Appointment Status:', 'The AI calls get_appointment_details in real time to verify appointment status — never relies solely on conversation history.'),
    ]

    styled_heading(doc, '9.2  Key Behavioral Rules (Summary)', 2)
    for bold_text, rest in rules:
        bullet_item(doc, rest, bold_prefix=bold_text)

    doc.add_paragraph()
    styled_heading(doc, '9.3  Tool Calling Interface', 2)
    body_para(doc, (
        'The AI uses structured function calling (supported by Google Gemini and Groq Llama-3) to interact '
        'with the backend. The following tools are available to the AI at runtime:'
    ))

    tools_table = doc.add_table(rows=9, cols=2)
    tools_table.style = 'Table Grid'

    hdr = tools_table.rows[0]
    for ci, txt in enumerate(('Tool / Function', 'What it Does')):
        set_cell_bg(hdr.cells[ci], '1E3A5F')
        r = hdr.cells[ci].paragraphs[0].add_run(txt)
        r.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(11)

    tools_data = [
        ('get_doctors',              'Returns all active doctors with specializations and weekly schedules.'),
        ('get_services',             'Returns services available for a specific doctor (doctor_id required).'),
        ('get_clinic_info',          'Returns clinic name, contact, hours, policies, and consultation fee.'),
        ('check_availability',       'Returns open appointment slots for a given doctor and date after applying shift rules, breaks, leaves, and existing bookings.'),
        ('book_appointment',         'Atomically validates overlap and inserts a new appointment record. Returns appointment ID on success.'),
        ('cancel_appointment',       'Cancels an existing appointment by ID. The slot immediately becomes available again.'),
        ('reschedule_appointment',   'Moves an existing appointment to a new date, time, doctor, or service.'),
        ('update_customer_details',  'Corrects the patient\'s name or phone number without affecting their appointment.'),
        ('human_handoff',            'Triggers HITL mode — pauses the AI and flags the conversation for staff takeover.'),
        ('get_appointment_details',  'Fetches live appointment status by phone number or appointment ID.'),
    ]

    for i, (tool, desc) in enumerate(tools_data):
        if i + 1 >= len(tools_table.rows):
            tools_table.add_row()
        row = tools_table.rows[i + 1]
        bg = 'DBEAFE' if i % 2 == 0 else 'FFFFFF'
        set_cell_bg(row.cells[0], bg)
        set_cell_bg(row.cells[1], bg)
        r0 = row.cells[0].paragraphs[0].add_run(tool)
        r0.bold = True
        r0.font.name = 'Courier New'
        r0.font.size = Pt(10)
        r0.font.color.rgb = DARK_BLUE
        r1 = row.cells[1].paragraphs[0].add_run(desc)
        r1.font.size = Pt(10.5)

    for row in tools_table.rows:
        row.cells[0].width = Inches(2.2)
        row.cells[1].width = Inches(5.0)

    doc.add_paragraph()
    add_horizontal_rule(doc)
    doc.add_paragraph()


# ── Section 10: ERD ────────────────────────────────────────────────────────────

def section_erd(doc):
    styled_heading(doc, '10. Database Design — Entity Relationship Diagram (ERD)', 1)

    body_para(doc, (
        'ClinicConnect AI uses a fully normalized relational database schema (PostgreSQL in production, '
        'SQLite in development) managed via SQLAlchemy ORM. The schema enforces strict multi-tenant isolation '
        'through a Business (clinic tenant) foreign key present on every entity. All tables are automatically '
        'migrated and column-patched at startup via the auto_migrate_db() utility.'
    ))

    doc.add_paragraph()
    styled_heading(doc, '10.1  Core Entities', 2)

    entities = [
        ('businesses', 'The top-level tenant entity. Every other record in the system is scoped to a business_id.',
         ['id (PK)', 'name', 'business_type', 'address', 'phone', 'email', 'timezone',
          'opening_hours', 'policies', 'consultation_fee',
          'subscription_status', 'subscription_start_date', 'trial_ends_at',
          'subscription_expires_at', 'active_plan_name', 'created_at', 'updated_at']),

        ('doctors', 'Represents a practicing physician or specialist within a clinic tenant.',
         ['id (PK)', 'business_id (FK → businesses)', 'name', 'specialization',
          'working_days', 'start_time', 'end_time',
          'shift_2_start_time', 'shift_2_end_time', 'slot_interval',
          'break_start_time', 'break_end_time', 'is_active',
          'created_at', 'updated_at']),

        ('doctor_schedules', 'Per-day recurring weekly schedule for each doctor. Overrides flat start/end on the Doctor record.',
         ['id (PK)', 'doctor_id (FK → doctors)', 'day_of_week',
          'is_available', 'start_time', 'end_time',
          'shift_2_start', 'shift_2_end']),

        ('doctor_leaves', 'Blocks specific calendar dates or partial-day windows for a doctor (conferences, vacations, etc.).',
         ['id (PK)', 'doctor_id (FK → doctors)', 'business_id (FK → businesses)',
          'leave_date', 'is_full_day', 'start_time', 'end_time', 'reason']),

        ('services', 'Medical services or treatments offered by a specific doctor, each with its own price and duration.',
         ['id (PK)', 'business_id (FK → businesses)', 'doctor_id (FK → doctors)',
          'name', 'description', 'duration', 'price', 'is_active']),

        ('customers', 'Patient contact records — created on first booking and reused across subsequent visits.',
         ['id (PK)', 'business_id (FK → businesses)',
          'name', 'phone', 'email', 'created_at']),

        ('appointments', 'The core transactional record for every scheduled visit. Has a partial unique index preventing double-booking.',
         ['id (PK)', 'business_id (FK → businesses)', 'customer_id (FK → customers)',
          'doctor_id (FK → doctors)', 'service_id (FK → services)',
          'appointment_date (YYYY-MM-DD)', 'appointment_time (HH:MM)',
          'status (CONFIRMED / CANCELLED / COMPLETED / PENDING)',
          'notes', 'conversation_id (FK → conversations)',
          'booked_by_phone', 'idempotency_key (UNIQUE)',
          'created_at', 'updated_at']),

        ('conversations', 'Tracks an active AI session — stores multi-turn workflow state, awaiting-input flags, and partial booking data.',
         ['id (PK)', 'business_id (FK → businesses)', 'customer_id (FK → customers)',
          'visitor_id', 'channel (web_chat / whatsapp)',
          'status (AI / HUMAN / CLOSED)',
          'intent', 'workflow_state', 'awaiting_input',
          'selected_doctor_id', 'selected_service_id',
          'requested_date', 'requested_time',
          'pending_customer_name', 'pending_customer_phone',
          'handoff_reason', 'created_at', 'updated_at']),

        ('messages', 'Individual chat messages within a conversation — stores role (user/assistant), content, and timestamp.',
         ['id (PK)', 'conversation_id (FK → conversations)',
          'role (user / assistant / system)', 'content',
          'created_at']),

        ('reminders', 'Scheduled appointment reminders dispatched via WhatsApp 24 hours before the appointment.',
         ['id (PK)', 'business_id (FK → businesses)',
          'appointment_id (FK → appointments)',
          'status (PENDING / SENT / FAILED)',
          'scheduled_at', 'sent_at']),

        ('users', 'Clinic staff and admin user accounts for portal login.',
         ['id (PK)', 'business_id (FK → businesses)',
          'username', 'password_hash', 'role (admin / staff)',
          'is_active', 'created_at']),

        ('subscription_requests', 'Tracks subscription upgrade or renewal requests submitted by clinic owners to the platform superadmin.',
         ['id (PK)', 'business_id (FK → businesses)',
          'plan_name', 'status (pending / approved / rejected)',
          'message', 'created_at']),

        ('whatsapp_accounts', 'WhatsApp Cloud API configuration per clinic — Phone Number ID, Access Token, and Verify Token.',
         ['id (PK)', 'business_id (FK → businesses)',
          'phone_number_id', 'access_token', 'verify_token',
          'display_name', 'is_active']),
    ]

    for table_name, desc, fields in entities:
        styled_heading(doc, table_name, 3)
        p_desc = doc.add_paragraph()
        p_desc.paragraph_format.space_after = Pt(4)
        rd = p_desc.add_run(desc)
        rd.italic = True
        rd.font.size = Pt(11)
        rd.font.color.rgb = MID_GRAY

        # Field table
        tbl = doc.add_table(rows=1, cols=1)
        tbl.style = 'Table Grid'
        set_cell_bg(tbl.rows[0].cells[0], 'F1F5F9')
        field_text = '  |  '.join(fields)
        r = tbl.rows[0].cells[0].paragraphs[0].add_run(field_text)
        r.font.name = 'Courier New'
        r.font.size = Pt(9)
        r.font.color.rgb = DARK_GRAY
        doc.add_paragraph()

    styled_heading(doc, '10.2  Key Relationships & Constraints', 2)

    relationships = [
        ('Business  ──<  Doctors',          'One clinic tenant owns many doctors. Cascade delete removes all doctor records when a clinic is deleted.'),
        ('Doctor    ──<  DoctorSchedules',   'One doctor has 7 DoctorSchedule rows (Mon–Sun). Per-day hours override flat start/end_time columns.'),
        ('Doctor    ──<  DoctorLeaves',      'One doctor can have many blocked leave dates. Leave records exclude those windows from slot generation.'),
        ('Doctor    ──<  Services',          'Services are doctor-scoped. A service belongs to one doctor only — never shared across doctors.'),
        ('Customer  ──<  Appointments',      'One patient can have many appointments over time. Customer record is reused via phone number lookup.'),
        ('Doctor    ──<  Appointments',      'One doctor can have many appointments. Partial unique index: (business_id, doctor_id, date, time) WHERE status = CONFIRMED prevents double-booking at the DB level.'),
        ('Conversation ──< Messages',        'One conversation session holds many messages in chronological order. Conversation stores workflow state across turns.'),
        ('Appointment ──< Reminders',        'One appointment can trigger multiple reminder records (e.g., 24h and 1h before). Status tracks dispatch success.'),
    ]

    rel_table = doc.add_table(rows=len(relationships) + 1, cols=2)
    rel_table.style = 'Table Grid'

    hdr_row = rel_table.rows[0]
    for ci, txt in enumerate(('Relationship', 'Description')):
        set_cell_bg(hdr_row.cells[ci], '1E40AF')
        r = hdr_row.cells[ci].paragraphs[0].add_run(txt)
        r.bold = True
        r.font.color.rgb = WHITE
        r.font.size = Pt(11)

    for i, (rel, desc) in enumerate(relationships):
        row = rel_table.rows[i + 1]
        bg = 'DBEAFE' if i % 2 == 0 else 'FFFFFF'
        set_cell_bg(row.cells[0], bg)
        set_cell_bg(row.cells[1], bg)
        r0 = row.cells[0].paragraphs[0].add_run(rel)
        r0.font.name = 'Courier New'
        r0.font.size = Pt(10)
        r0.bold = True
        r0.font.color.rgb = NAVY
        r1 = row.cells[1].paragraphs[0].add_run(desc)
        r1.font.size = Pt(10.5)

    for row in rel_table.rows:
        row.cells[0].width = Inches(2.4)
        row.cells[1].width = Inches(4.8)

    doc.add_paragraph()
    figure_placeholder(doc, '8.0',
                       'Full Entity Relationship Diagram (ERD)',
                       'Visual ERD showing all 14 tables, primary keys, foreign keys, and cardinality relationships')

    doc.add_paragraph()
    add_horizontal_rule(doc)
    doc.add_paragraph()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'ClinicConnect_AI_Evaluation_Report_v2.docx')

    print('[+] Creating document...')
    doc = create_document()

    print('[+] Cover page...')
    cover_page(doc)

    print('[+] Table of contents...')
    table_of_contents(doc)

    print('[+] Section 1: Overview...')
    section_overview(doc)

    print('[+] Section 2: Features...')
    section_features(doc)

    print('[+] Section 3: Architecture...')
    section_architecture(doc)

    print('[+] Section 4: Tech Stack...')
    section_tech_stack(doc)

    print('[+] Section 5: Live Demo...')
    section_live_demo(doc)

    print('[+] Section 6: GitHub...')
    section_github(doc)

    print('[+] Section 7: Contributions...')
    section_contributions(doc)

    print('[+] Section 8: Screenshots...')
    section_screenshots(doc)

    print('[+] Section 9: AI Prompt Design...')
    section_ai_prompt_design(doc)

    print('[+] Section 10: ERD...')
    section_erd(doc)

    print('[+] Header & footer...')
    add_header_footer(doc)

    print(f'[+] Saving to: {output_path}')
    doc.save(output_path)
    print(f'\n[OK] Document generated successfully!\n   -> {output_path}')
    print(f'   File size: {os.path.getsize(output_path):,} bytes')


if __name__ == '__main__':
    main()
