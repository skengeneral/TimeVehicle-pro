import os
import sys
from datetime import datetime
from pathlib import Path

def save_to_excel(data_cards, custom_columns=None):
    """
    Accepts the array of processed extraction data cards and structures them 
    into a pristine Excel matrix, running completely out of system RAM.
    """
    if not data_cards:
        return "No Data"

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise Exception("Required library 'openpyxl' is missing inside the execution runtime.")

    # 🟢 FIXED FOR PRO: Detects the directory where the user launched the .exe file
    if getattr(sys, 'frozen', False):
        output_dir = Path(sys.executable).parent
    else:
        output_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"timevehicle1.0_Export_{timestamp}.xlsx"
    output_filepath = output_dir / filename

    # --- Robust Layout Structure Handling ---
    default_structure = [
        ("Business Name", "Business Name"),
        ("Google Rating", "Google Rating"),
        ("Complete Address", "Complete Address"),
        ("Operating Hours Matrix", "Operating Hours Matrix"),
        ("Website Link", "Website Link"),
        ("Email ID", "Email ID"),
        ("Phone Number", "Phone Number"),
        ("Facebook Handle", "Facebook Handle"),
        ("Instagram Handle", "Instagram Handle"),
        ("LinkedIn Handle", "LinkedIn Handle"),
        ("Twitter/X Handle", "Twitter/X Handle")
    ]

    columns_to_build = []
    if custom_columns:
        for item in custom_columns:
            if isinstance(item, tuple):
                columns_to_build.append(item)
            else:
                columns_to_build.append((item, item))
    else:
        columns_to_build = default_structure

    # Spin up the native excel instances out of RAM
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compiled Leads Matrix"
    ws.views.sheetView[0].showGridLines = True

    # Styling Presets
    font_header = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="Segoe UI", size=10, bold=False, color="000000")
    fill_header = PatternFill(start_color="002D4A", end_color="002D4A", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=False)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=False)
    thin_side = Side(border_style="thin", color="E2E8F0")
    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # Build Header Row
    for col_idx, (_, display_name) in enumerate(columns_to_build, start=1):
        cell = ws.cell(row=1, column=col_idx, value=display_name)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = cell_border
    ws.row_dimensions[1].height = 26

    # Build Data Rows
    for row_idx, card in enumerate(data_cards, start=2):
        for col_idx, (dict_key, _) in enumerate(columns_to_build, start=1):
            raw_value = card.get(dict_key, "Not Provided")
            if raw_value is None or str(raw_value).strip() == "":
                raw_value = "Not Provided"

            cell = ws.cell(row=row_idx, column=col_idx, value=raw_value)
            cell.font = font_data
            cell.border = cell_border
            
            if dict_key in ["Google Rating", "Phone Number"]:
                cell.alignment = align_center
            else:
                cell.alignment = align_left
        ws.row_dimensions[row_idx].height = 20

    # Auto-adjust column width adjustments dynamically
    for col_idx in range(1, len(columns_to_build) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for cell in ws[col_letter]:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Commit write properties to hardware
    try:
        wb.save(str(output_filepath))
        return os.path.abspath(str(output_filepath))
    except Exception as e:
        print(f"❌ Primary disk write failure: {str(e)}")
        try:
            fallback_path = Path(filename).resolve()
            wb.save(str(fallback_path))
            return str(fallback_path)
        except:
            return "Generation Error"

def save_to_word(data_cards):
    """
    Optional fallback documentation generator. Appends social anchors 
    neatly at the bottom of each structural text section.
    """
    pass
