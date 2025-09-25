from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from django.shortcuts import render
from datetime import datetime, timedelta
import json
import csv
from io import StringIO, BytesIO
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from .models import Equipment, MaintenanceLog, SupportTicket
from .forms import AdvancedReportForm

class AdvancedReportsView(LoginRequiredMixin, View):
    def get(self, request):
        form = AdvancedReportForm(request.GET or None)
        report_data = None
        charts_data = None
        
        if form.is_valid():
            report_data = self.generate_report_data(form.cleaned_data)
            charts_data = self.generate_charts_data(form.cleaned_data, report_data)
            
            # Exportar si se solicita
            export_format = form.cleaned_data.get('export_format')
            if export_format and export_format != 'html':
                return self.export_report(export_format, report_data, charts_data, form.cleaned_data)
        
        context = {
            'form': form,
            'report_data': report_data,
            'charts_data': charts_data,
        }
        return render(request, 'reports/advanced_reports.html', context)
    
    def generate_report_data(self, form_data):
        report_type = form_data['report_type']
        date_range = form_data['date_range']
        start_date, end_date = self.get_date_range(date_range, form_data)
        
        data = {
            'metadata': {
                'report_type': report_type,
                'date_range': f"{start_date} to {end_date}",
                'generated_at': timezone.now()
            }
        }
        
        if report_type == 'equipment_summary':
            data.update(self.equipment_summary_report(start_date, end_date, form_data))
        elif report_type == 'maintenance_costs':
            data.update(self.maintenance_costs_report(start_date, end_date, form_data))
        elif report_type == 'ticket_analysis':
            data.update(self.ticket_analysis_report(start_date, end_date, form_data))
        elif report_type == 'warranty_status':
            data.update(self.warranty_status_report(form_data))
        elif report_type == 'performance_metrics':
            data.update(self.performance_metrics_report(start_date, end_date, form_data))
        
        return data
    
    def equipment_summary_report(self, start_date, end_date, form_data):
        # Equipos por tipo y estado
        equipment_data = Equipment.objects.all()
        
        # Aplicar filtros
        if form_data.get('equipment_type'):
            equipment_data = equipment_data.filter(type__in=form_data['equipment_type'])
        
        if form_data.get('status_filter'):
            equipment_data = equipment_data.filter(status__in=form_data['status_filter'])
        
        summary = {
            'total_equipment': equipment_data.count(),
            'by_type': list(equipment_data.values('type').annotate(count=Count('id'))),
            'by_status': list(equipment_data.values('status').annotate(count=Count('id'))),
            'by_location': list(equipment_data.values('location').annotate(count=Count('id')).order_by('-count')[:10]),
            'acquisition_timeline': self.get_acquisition_timeline(equipment_data, start_date, end_date)
        }
        
        return {'equipment_summary': summary}
    
    def maintenance_costs_report(self, start_date, end_date, form_data):
        maintenance_data = MaintenanceLog.objects.filter(
            start_date__range=[start_date, end_date]
        )
        
        costs_summary = {
            'total_maintenance': maintenance_data.count(),
            'total_cost': maintenance_data.aggregate(total=Sum('cost'))['total'] or 0,
            'avg_cost': maintenance_data.aggregate(avg=Avg('cost'))['avg'] or 0,
            'by_type': list(maintenance_data.values('maintenance_type').annotate(
                count=Count('id'), total_cost=Sum('cost')
            )),
            'by_technician': list(maintenance_data.values('technician__user__username').annotate(
                count=Count('id'), total_cost=Sum('cost')
            ).order_by('-total_cost')[:10]),
            'monthly_trend': self.get_monthly_cost_trend(start_date, end_date)
        }
        
        return {'maintenance_costs': costs_summary}
    
    def ticket_analysis_report(self, start_date, end_date, form_data):
        tickets_data = SupportTicket.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        analysis = {
            'total_tickets': tickets_data.count(),
            'by_status': list(tickets_data.values('status').annotate(count=Count('id'))),
            'by_priority': list(tickets_data.values('priority').annotate(count=Count('id'))),
            'resolution_time': self.calculate_avg_resolution_time(tickets_data),
            'by_assignee': list(tickets_data.values('assigned_to__user__username').annotate(
                count=Count('id')
            ).order_by('-count')[:10]),
            'trends': self.get_ticket_trends(start_date, end_date)
        }
        
        return {'ticket_analysis': analysis}
    
    def warranty_status_report(self, form_data):
        equipment_data = Equipment.objects.filter(warranty_expiry__isnull=False)
        
        today = timezone.now().date()
        warranty_status = {
            'total_with_warranty': equipment_data.count(),
            'active': equipment_data.filter(warranty_expiry__gt=today).count(),
            'expiring_30_days': equipment_data.filter(
                warranty_expiry__range=[today, today + timedelta(days=30)]
            ).count(),
            'expired': equipment_data.filter(warranty_expiry__lt=today).count(),
            'by_month': self.get_warranty_expiry_by_month(equipment_data),
            'critical_equipment': equipment_data.filter(
                warranty_expiry__range=[today, today + timedelta(days=30)]
            ).values('brand', 'model', 'serial_number', 'warranty_expiry')
        }
        
        return {'warranty_status': warranty_status}
    
    def performance_metrics_report(self, start_date, end_date, form_data):
        metrics = {
            'equipment_uptime': self.calculate_uptime_metrics(start_date, end_date),
            'maintenance_efficiency': self.calculate_maintenance_efficiency(start_date, end_date),
            'ticket_performance': self.calculate_ticket_performance(start_date, end_date),
            'cost_effectiveness': self.calculate_cost_effectiveness(start_date, end_date)
        }
        
        return {'performance_metrics': metrics}
    
    # Métodos auxiliares para cálculos
    def get_date_range(self, date_range, form_data):
        today = timezone.now().date()
        
        if date_range == 'last_7_days':
            return today - timedelta(days=7), today
        elif date_range == 'last_30_days':
            return today - timedelta(days=30), today
        elif date_range == 'last_90_days':
            return today - timedelta(days=90), today
        elif date_range == 'last_year':
            return today - timedelta(days=365), today
        elif date_range == 'custom':
            return form_data['start_date'], form_data['end_date']
        
        return today - timedelta(days=30), today
    
    def generate_charts_data(self, form_data, report_data):
        report_type = form_data['report_type']
        
        if report_type == 'equipment_summary':
            return self.generate_equipment_charts(report_data['equipment_summary'])
        elif report_type == 'maintenance_costs':
            return self.generate_maintenance_charts(report_data['maintenance_costs'])
        elif report_type == 'ticket_analysis':
            return self.generate_ticket_charts(report_data['ticket_analysis'])
        elif report_type == 'warranty_status':
            return self.generate_warranty_charts(report_data['warranty_status'])
        
        return {}
    
    def generate_equipment_charts(self, data):
        return {
            'type_pie_chart': {
                'labels': [item['type'] for item in data['by_type']],
                'data': [item['count'] for item in data['by_type']]
            },
            'status_bar_chart': {
                'labels': [item['status'] for item in data['by_status']],
                'data': [item['count'] for item in data['by_status']]
            }
        }
    
    def export_report(self, format, report_data, charts_data, form_data):
        if format == 'pdf':
            return self.export_to_pdf(report_data, form_data)
        elif format == 'excel':
            return self.export_to_excel(report_data, form_data)
        elif format == 'csv':
            return self.export_to_csv(report_data, form_data)
        
        return HttpResponse("Formato no soportado")
    
    def export_to_pdf(self, report_data, form_data):
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        elements.append(Paragraph(f"Reporte: {form_data['report_type']}", styles['Title']))
        elements.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        
        # Aquí agregar más contenido al PDF...
        
        doc.build(elements)
        return response
    
    def export_to_excel(self, report_data, form_data):
        # Implementar exportación a Excel
        pass
    
    def export_to_csv(self, report_data, form_data):
        # Implementar exportación a CSV
        pass

# Vista para gráficos interactivos via API
class ChartsDataAPIView(LoginRequiredMixin, View):
    def get(self, request):
        chart_type = request.GET.get('type', 'equipment_by_type')
        date_range = request.GET.get('date_range', 'last_30_days')
        
        data = self.get_chart_data(chart_type, date_range)
        return JsonResponse(data)
    
    def get_chart_data(self, chart_type, date_range):
        # Lógica para generar datos de gráficos específicos
        if chart_type == 'equipment_by_type':
            return self.get_equipment_by_type_data()
        elif chart_type == 'maintenance_costs_trend':
            return self.get_maintenance_costs_trend_data(date_range)
        # ... más tipos de gráficos
        
        return {}