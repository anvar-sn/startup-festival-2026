import io
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def generate_applications_excel(queryset=None) -> io.BytesIO:
    """Barcha arizalarni formatlangan chiroyli Excel faylga eksport qiladi."""
    if queryset is None:
        from core.models import Application
        queryset = Application.objects.select_related("participant", "participant__project", "participant__project__category").prefetch_related("participant__project__files").all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Startup Arizalar 2026"
    ws.views.sheetView[0].showGridLines = True

    # Ranglar va shriftlar
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    regular_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    # Status ranglari
    status_fills = {
        "new": PatternFill(start_color="E0F2FE", end_color="E0F2FE", fill_type="solid"),
        "review": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
        "approved": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
        "rejected": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
    }

    headers = [
        "№",
        "Ariza raqami",
        "Holati",
        "Ishtirokchi F.I.SH",
        "Telefon",
        "Telegram",
        "Guruh",
        "Ta'lim yo'nalishi",
        "Tug'ilgan sana",
        "Loyiha nomi",
        "Yo'nalish",
        "Havola (Link)",
        "Qisqacha tavsifi",
        "Muammo",
        "Maqsad",
        "Yangilik va afzalliklari",
        "Ishlash mexanizmi",
        "Kelajak istiqboli",
        "Fayllar",
        "Yuborilgan sana",
    ]

    # Sarlavha qatorini yozish
    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border

    # Ma'lumotlarni yozish
    for idx, app in enumerate(queryset, 1):
        p = app.participant
        pr = getattr(app, "project", None)
        
        files_str = ""
        if pr:
            f_kinds = [f.get_kind_display() for f in pr.files.all()]
            files_str = ", ".join(f_kinds) if f_kinds else "Fayl yo'q"

        row = [
            idx,
            app.number or f"SLF26-{app.pk:05d}",
            app.get_status_display(),
            p.full_name(),
            p.phone,
            f"@{p.telegram_username.lstrip('@')}" if p.telegram_username else "-",
            p.group,
            p.study_direction,
            p.birth_date.strftime("%d.%m.%Y") if p.birth_date else "-",
            pr.title if pr else "-",
            pr.category.name if pr and pr.category else "-",
            pr.link if pr and pr.link else "-",
            pr.summary if pr else "-",
            pr.problem if pr else "-",
            pr.goal if pr else "-",
            pr.novelty if pr else "-",
            pr.mechanism if pr else "-",
            pr.future if pr else "-",
            files_str,
            app.created_at.strftime("%d.%m.%Y %H:%M"),
        ]
        ws.append(row)
        row_num = idx + 1
        ws.row_dimensions[row_num].height = 24

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.font = regular_font
            cell.border = border
            if col_idx in (1, 2, 5, 6, 7, 9, 20):
                cell.alignment = center_align
            else:
                cell.alignment = left_align

            # Status ustuniga mos rang berish
            if col_idx == 3:
                fill = status_fills.get(app.status)
                if fill:
                    cell.fill = fill
                cell.alignment = center_align

    # Ustun kengliklarini avtomatik moslash
    min_widths = {
        1: 6,   # №
        2: 16,  # Ariza raqami
        3: 18,  # Holati
        4: 28,  # F.I.SH
        5: 18,  # Telefon
        6: 16,  # Telegram
        7: 12,  # Guruh
        8: 24,  # Ta'lim yo'nalishi
        9: 14,  # Tug'ilgan sana
        10: 28, # Loyiha nomi
        11: 22, # Yo'nalish
        12: 24, # Havola
        13: 35, # Qisqacha
        14: 35, # Muammo
        15: 35, # Maqsad
        16: 35, # Yangilik
        17: 35, # Mexanizm
        18: 35, # Kelajak
        19: 20, # Fayllar
        20: 18, # Sana
    }
    for col_idx, width in min_widths.items():
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # Auto filter
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(queryset) + 1}"

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
