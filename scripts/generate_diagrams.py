"""
Generate high-resolution, professional diagrams for ClinicConnect AI:
1. System Architecture Diagram (Layered Architecture)
2. AI Booking Pipeline Sequence Diagram (UML Sequence)
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_system_architecture_diagram(output_path):
    # Generous dimensions to prevent any overlap
    fig, ax = plt.subplots(figsize=(15, 12), dpi=300)
    fig.patch.set_facecolor('#F8FAFC')
    ax.set_facecolor('#F8FAFC')
    
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 12.2)
    ax.axis('off')
    
    # Title
    ax.text(7.5, 11.75, "ClinicConnect AI — System Architecture Diagram", 
            ha='center', va='center', fontsize=20, fontweight='bold', color='#1E3A5F', family='sans-serif')
    ax.text(7.5, 11.35, "Multi-Tenant Omnichannel Conversational AI & Clinic Operations SaaS", 
            ha='center', va='center', fontsize=12, color='#64748B', family='sans-serif')
    
    # Helper to draw a layer box
    def draw_layer_container(y, height, title, subtitle):
        rect = patches.FancyBboxPatch((0.6, y), 13.8, height, boxstyle="round,pad=0.1,rounding_size=0.2",
                                      linewidth=1.2, edgecolor='#CBD5E1', facecolor='#FFFFFF')
        ax.add_patch(rect)
        
        # Layer Header Tag
        tag = patches.FancyBboxPatch((0.9, y + height - 0.40), 4.6, 0.34, boxstyle="round,pad=0.05,rounding_size=0.08",
                                     linewidth=0, facecolor='#F1F5F9')
        ax.add_patch(tag)
        ax.text(1.1, y + height - 0.23, title, fontsize=9.5, fontweight='bold', color='#1E293B', va='center')
        if subtitle:
            ax.text(5.7, y + height - 0.23, f"— {subtitle}", fontsize=9, color='#64748B', va='center', style='italic')

    # Helper to draw component box with ample breathing room
    def draw_component(x, y, w, h, title, sub_badge, desc_items, color='#2563EB'):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                      linewidth=1.3, edgecolor=color, facecolor='#FFFFFF')
        ax.add_patch(rect)
        
        # Top banner on component
        top_bar = patches.FancyBboxPatch((x, y + h - 0.40), w, 0.40, boxstyle="round,pad=0.05,rounding_size=0.1",
                                         linewidth=0, facecolor=color)
        ax.add_patch(top_bar)
        ax.text(x + w/2, y + h - 0.20, title, fontsize=10, fontweight='bold', color='#FFFFFF', ha='center', va='center')
        
        # Sub-badge under banner
        cur_y = y + h - 0.62
        if sub_badge:
            ax.text(x + w/2, cur_y, sub_badge.upper(), fontsize=7.2, color=color, fontweight='bold', ha='center', va='center')
            cur_y -= 0.22
            
        # Divider line
        ax.plot([x + 0.3, x + w - 0.3], [cur_y + 0.08, cur_y + 0.08], color='#E2E8F0', lw=0.8)
        cur_y -= 0.12

        # Description bullet items
        for item in desc_items:
            ax.text(x + 0.22, cur_y, f"• {item}", fontsize=8.2, color='#334155', ha='left', va='top')
            cur_y -= 0.25

    # Layer 1: Patient Channels (y = 8.8, h = 2.1)
    draw_layer_container(8.8, 2.1, "1. PATIENT CLIENT LAYER", "Omnichannel Healthcare Ingestion")
    draw_component(1.0, 9.0, 3.8, 1.45, "WhatsApp Cloud API", "Official Meta Graph API",
                   ["Real-time Webhook Ingestion", "Audio Voice Notes & Text Support", "Session & Message ID Tracking"], 
                   '#15803D')
    draw_component(5.6, 9.0, 3.8, 1.45, "Web Chat AI Widget", "Modern Web Client",
                   ["Responsive Embedded Widget", "Live Session Synchronization", "Strict 12-Hour AM/PM Displays"], 
                   '#0284C7')
    draw_component(10.2, 9.0, 3.8, 1.45, "Future Channels", "Expansion Roadmap",
                   ["Instagram Direct Messaging", "Facebook Messenger & SMS", "Interactive Voice (IVR) Agent"], 
                   '#9333EA')

    # Layer 2: API Gateway & Ingestion (y = 6.4, h = 2.1)
    draw_layer_container(6.4, 2.1, "2. INGESTION & GATEWAY LAYER", "Security, Blueprints & Tenant Routing")
    draw_component(1.0, 6.6, 3.8, 1.45, "Webhook Signature Verifier", "HMAC SHA-256 Guard",
                   ["Payload Hash Authentication", "Replay Attack Prevention", "Instant 200 OK Handshake"], 
                   '#D97706')
    draw_component(5.6, 6.6, 3.8, 1.45, "Flask Application Gateway", "Core WSGI Gateway",
                   ["Modular Blueprints Architecture", "Cross-Origin & Header Defense", "Asynchronous Event Dispatching"], 
                   '#2563EB')
    draw_component(10.2, 6.6, 3.8, 1.45, "Tenant Auth Guard", "Multi-Tenant Isolation",
                   ["Session & Cookie Authentication", "Strict business_id Query Scoping", "Staff vs Platform Superadmin"], 
                   '#4338CA')

    # Layer 3: Agentic Intelligence & Business Logic (y = 3.6, h = 2.5)
    draw_layer_container(3.6, 2.5, "3. AGENTIC AI & BUSINESS LOGIC LAYER", "Autonomous Reasoning & Atomic Scheduling")
    draw_component(1.0, 3.8, 2.9, 1.85, "AI Receptionist", "ai/prompts.py",
                   ["Dynamic System Prompt", "Urdu / Roman Urdu / English", "Doctor-First Polyclinic Flow", "Inviolable Confirmation Gate"], 
                   '#1E3A5F')
    draw_component(4.4, 3.8, 2.9, 1.85, "LLM Engine", "Gemini 2.5 / Groq",
                   ["Zero-Shot Entity Extraction", "Structured Function Calling", "Intent Classification Machine", "Context History Window"], 
                   '#0F766E')
    draw_component(7.8, 3.8, 2.9, 1.85, "BookingService", "services/booking.py",
                   ["Atomic Overlap Resolution", "Partial Unique Constraint DB", "Idempotent Transaction Logic", "Human Name Verification"], 
                   '#BE123C')
    draw_component(11.2, 3.8, 2.9, 1.85, "ScheduleService", "services/schedule.py",
                   ["Shift 1 & Shift 2 Calculator", "Lunch Break Window Exclusion", "Doctor Blocked Dates/Leaves", "1-Click Schedule Presets"], 
                   '#B45309')

    # Layer 4: Persistence & External Layer (y = 1.25, h = 2.05)
    draw_layer_container(1.25, 2.05, "4. PERSISTENCE & TASK ORCHESTRATION LAYER", "Relational Storage & Cloud Dispatch")
    draw_component(1.0, 1.42, 3.8, 1.45, "Relational Database", "PostgreSQL / SQLite",
                   ["13 Multi-Tenant Tables", "Foreign Key Cascade Defense", "Partial Unique Indexes for Slots"], 
                   '#1E40AF')
    draw_component(5.6, 1.42, 3.8, 1.45, "Celery & Task Runner", "Background Orchestrator",
                   ["Automated Reminder Queue", "24-Hour & 1-Hour Notifications", "Exponential Backoff Retries"], 
                   '#B91C1C')
    draw_component(10.2, 1.42, 3.8, 1.45, "External Cloud Services", "Cloud Connectors",
                   ["Meta WhatsApp Cloud API", "Whisper STT / ElevenLabs TTS", "Render Production PaaS & SSL"], 
                   '#047857')

    # Layer 5: Operations Consoles (y = 0.05, h = 0.95)
    rect5 = patches.FancyBboxPatch((0.6, 0.05), 13.8, 0.95, boxstyle="round,pad=0.08,rounding_size=0.15",
                                   linewidth=1.2, edgecolor='#10B981', facecolor='#F0FDF4')
    ax.add_patch(rect5)
    ax.text(0.9, 0.72, "5. ADMINISTRATIVE & OPERATIONS CONSOLES", fontsize=10, fontweight='bold', color='#065F46')
    ax.text(1.1, 0.44, "• Clinic Operations Portal (/admin): Executive KPIs | Doctor Schedules & Shifts | Visual Slot Occupancy | HITL Chat Takeover | Topbar Search", fontsize=8.5, color='#047857')
    ax.text(1.1, 0.20, "• Platform Owner Console (/platform): Multi-Clinic Onboarding | Plan Gates & Expiration Telemetry | Seamless Clinic Context Switcher", fontsize=8.5, color='#047857')

    # Draw Connecting Arrows
    def draw_down_arrow(x, y1, y2, label=""):
        ax.annotate('', xy=(x, y2), xytext=(x, y1),
                    arrowprops=dict(facecolor='#475569', edgecolor='#475569', width=1.8, headwidth=7, headlength=8))
        if label:
            ax.text(x + 0.12, (y1 + y2)/2, label, fontsize=8, color='#334155', va='center', fontweight='bold')

    # Arrows from Layer 1 to 2
    draw_down_arrow(2.9, 9.0, 8.5, "Webhook Event")
    draw_down_arrow(7.5, 9.0, 8.5, "REST / JSON")
    
    # Arrows from Layer 2 to 3
    draw_down_arrow(7.5, 6.6, 6.1, "Authenticated Request")
    
    # Horizontal Arrows between Logic components
    ax.annotate('', xy=(4.4, 4.7), xytext=(3.9, 4.7),
                arrowprops=dict(arrowstyle="<->", color='#475569', lw=1.8))
    ax.annotate('', xy=(7.8, 4.7), xytext=(7.3, 4.7),
                arrowprops=dict(arrowstyle="->", color='#475569', lw=1.8))
    ax.annotate('', xy=(11.2, 4.7), xytext=(10.7, 4.7),
                arrowprops=dict(arrowstyle="<->", color='#475569', lw=1.8))

    # Arrows from Layer 3 to 4
    draw_down_arrow(2.9, 3.8, 3.3, "SQLAlchemy")
    draw_down_arrow(7.5, 3.8, 3.3, "Atomic Commit")
    draw_down_arrow(12.1, 3.8, 3.3, "Reminders")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] System Architecture Diagram saved to {output_path}")


def generate_booking_pipeline_diagram(output_path):
    # Generous height: 14.5 units for 15 steps
    fig, ax = plt.subplots(figsize=(15, 14.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 14.8)
    ax.axis('off')
    
    # Title
    ax.text(7.5, 14.35, "ClinicConnect AI — Autonomous AI Booking Pipeline", 
            ha='center', va='center', fontsize=20, fontweight='bold', color='#1E3A5F', family='sans-serif')
    ax.text(7.5, 13.95, "End-to-End UML Sequence: Multi-Turn Reasoning, Atomic Conflict Resolution & Live Sync", 
            ha='center', va='center', fontsize=11.5, color='#64748B', family='sans-serif')

    # Swimlane Columns
    cols = [
        ("PATIENT", "Web Chat / WhatsApp", 1.6, '#10B981'),
        ("AI RECEPTIONIST", "Gemini / Groq LLM", 4.6, '#1E3A5F'),
        ("BOOKING SERVICE", "Atomic Slot Engine", 7.6, '#2563EB'),
        ("DATABASE", "PostgreSQL / SQLite", 10.4, '#7C3AED'),
        ("CLINIC ADMIN", "Dashboard / Portal", 13.2, '#D97706')
    ]
    
    # Draw Column Headers & Vertical Lifelines
    for title, sub, x, color in cols:
        header_box = patches.FancyBboxPatch((x - 1.2, 13.0), 2.4, 0.72, boxstyle="round,pad=0.08,rounding_size=0.12",
                                            linewidth=1.3, edgecolor=color, facecolor=color)
        ax.add_patch(header_box)
        ax.text(x, 13.45, title, fontsize=10, fontweight='bold', color='#FFFFFF', ha='center', va='center')
        ax.text(x, 13.18, sub, fontsize=8, color='#F8FAFC', ha='center', va='center')
        
        # Lifeline down to bottom
        ax.plot([x, x], [0.8, 13.0], color='#CBD5E1', linestyle='--', linewidth=1.3, zorder=1)

    # 15 Sequence Steps (y_pos, from_col, to_col, label, desc, step_num, is_return, highlight)
    steps = [
        (12.3, 1.6, 4.6, '1', '"I want to book an appointment with Dr. Sara Malik tomorrow"', 'Patient message from WhatsApp / Webchat', False, False),
        (11.5, 4.6, 7.6, '2', 'check_availability(doctor_id=2, date="2026-09-24")', 'AI invokes availability tool via structured LLM tool call', False, False),
        (10.7, 7.6, 10.4, '3', 'Query DoctorSchedule + Shifts + Leaves', 'Retrieves active shifts (Shift 1/2), lunch breaks & blocked dates', False, False),
        (9.9, 10.4, 7.6, '4', 'Return Active Time Windows', 'Raw working shifts for selected day (e.g. 09:00 AM - 05:00 PM)', True, False),
        (9.1, 7.6, 10.4, '5', 'SELECT appointments WHERE doctor_id=2 AND status="CONFIRMED"', 'Filters occupied slots to guarantee zero double-booking', False, False),
        (8.3, 10.4, 7.6, '6', 'Return Occupied Slots: [10:00 AM, 11:30 AM]', 'Existing bookings retrieved from relational DB', True, False),
        (7.5, 7.6, 4.6, '7', 'Open Slots: [09:00 AM, 09:30 AM, 02:30 PM, 04:00 PM]', 'Available slots calculated in user-friendly 12-hour format', True, False),
        (6.7, 4.6, 1.6, '8', '"Dr. Sara is available at 09:30 AM and 02:30 PM. Which suits you?"', 'AI presents 12-hour formatted options politely in patient language', True, False),
        (5.9, 1.6, 4.6, '9', '"02:30 PM. Name: Raheema Kashif, Phone: 0329-9195999"', 'Patient confirms time slot and supplies full human credentials', False, False),
        (5.1, 4.6, 7.6, '10', 'book_appointment(doctor=2, date="2026-09-24", time="14:30", name, phone)', 'AI validates human name and invokes atomic booking function', False, True),
        (4.3, 7.6, 10.4, '11', 'BEGIN TRANSACTION: Re-check overlap + INSERT into appointments', 'Database level partial unique index ensures strict ACID safety', False, True),
        (3.5, 10.4, 7.6, '12', 'COMMIT: Appointment ID #28 Created', 'Atomic insertion confirmed, customer record linked', True, False),
        (2.7, 7.6, 4.6, '13', 'Success (Appointment #28, Raheema Kashif, 02:30 PM)', 'BookingService returns confirmed state to AI Orchestrator', True, False),
        (1.9, 4.6, 1.6, '14', '"Your appointment has been successfully booked and confirmed! (ID #28)"', 'Rich confirmation message delivered with date, doctor, fee & time', True, True),
        (1.1, 7.6, 13.2, '15', 'Live Sync: Update Dashboard Telemetry & Slot Matrix', 'Receptionist dashboard automatically shows new booking and alerts', False, True),
    ]

    for y, x1, x2, num, msg, subtext, is_ret, is_hl in steps:
        line_color = '#BE123C' if is_hl else ('#2563EB' if not is_ret else '#0D9488')
        line_style = '--' if is_ret else '-'
        
        # Draw arrow line
        ax.annotate('', xy=(x2, y), xytext=(x1, y),
                    arrowprops=dict(facecolor=line_color, edgecolor=line_color, 
                                    linestyle=line_style, lw=1.6, headwidth=6, headlength=7))
        
        # Step Number Badge floating above the arrow near start
        badge_x = x1 + (0.35 if x1 < x2 else -0.35)
        circle = patches.Circle((badge_x, y + 0.16), 0.16, facecolor=line_color, edgecolor='#FFFFFF', lw=1.2, zorder=5)
        ax.add_patch(circle)
        ax.text(badge_x, y + 0.16, num, color='#FFFFFF', fontsize=7.5, fontweight='bold', ha='center', va='center', zorder=6)
        
        # Message Text above arrow
        mid_x = (x1 + x2) / 2
        ax.text(mid_x, y + 0.16, msg, fontsize=8.6, fontweight='bold' if is_hl else 'semibold', 
                color='#0F172A', ha='center', va='bottom')
        if subtext:
            ax.text(mid_x, y - 0.18, subtext, fontsize=7.4, color='#64748B', ha='center', va='top', style='italic')

    # Security & Integrity Callout Box at bottom
    callout = patches.FancyBboxPatch((0.6, 0.12), 13.8, 0.46, boxstyle="round,pad=0.05,rounding_size=0.08",
                                     linewidth=1, edgecolor='#CBD5E1', facecolor='#F8FAFC')
    ax.add_patch(callout)
    ax.text(7.5, 0.35, "CRITICAL GUARANTEE: Inviolable Booking Gate prevents double-booking. Slots are validated in real-time and committed via ACID transactions.",
            ha='center', va='center', fontsize=8.8, color='#334155', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print(f"[OK] AI Booking Pipeline Sequence Diagram saved to {output_path}")

if __name__ == '__main__':
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    arch_path = os.path.join(docs_dir, 'clinicconnect_system_architecture_clean.png')
    seq_path = os.path.join(docs_dir, 'clinicconnect_booking_pipeline_clean.png')
    
    generate_system_architecture_diagram(arch_path)
    generate_booking_pipeline_diagram(seq_path)
