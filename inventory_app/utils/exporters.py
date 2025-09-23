 
import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

def export_equipment_to_excel(queryset):
    data = []
    for item in queryset:
        data.append({
            'Type': item.get_type_display(),
            'Brand': item.brand,
            'Model': item.model,
            'Serial Number': item.serial_number,
            'Purchase Date': item.purchase_date.strftime('%Y-%m-%d') if item.purchase_date else '',
            'Warranty Expiry': item.warranty_expiry.strftime('%Y-%m-%d') if item.warranty_expiry else '',
            'Location': item.location,
            'Status': item.get_status_display(),
            'Assigned To': str(item.assigned_to) if item.assigned_to else 'None',
            'Notes': item.notes
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Equipment', index=False)
        
        # Auto-adjust columns width
        worksheet = writer.sheets['Equipment']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    return response

def export_equipment_to_pdf(queryset):
    response = HttpResponse(content_type='application/pdf')
    filename = f"equipment_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=30,
    )
    
    # Title
    elements.append(Paragraph("Equipment Inventory Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.2 * inch))
    
    # Table data
    data = [['Type', 'Brand', 'Model', 'Serial', 'Location', 'Status']]
    
    for item in queryset:
        data.append([
            item.get_type_display(),
            item.brand,
            item.model,
            item.serial_number,
            item.location,
            item.get_status_display()
        ])
    
    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#D9E1F2')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return response

def export_maintenance_to_excel(queryset):
    data = []
    for item in queryset:
        data.append({
            'Equipment': str(item.equipment),
            'Type': item.get_maintenance_type_display(),
            'Title': item.title,
            'Technician': str(item.technician),
            'Start Date': item.start_date.strftime('%Y-%m-%d %H:%M'),
            'End Date': item.end_date.strftime('%Y-%m-%d %H:%M') if item.end_date else '',
            'Cost': float(item.cost) if item.cost else 0,
            'Priority': item.get_priority_display(),
            'Description': item.description,
            'Resolution': item.resolution
        })
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Maintenance', index=False)
        
        # Auto-adjust columns width
        worksheet = writer.sheets['Maintenance']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    return response