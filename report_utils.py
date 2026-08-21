"""
report_utils.py - Generate downloadable reports for the main forecast chart
"""

import io
import pandas as pd
from datetime import datetime
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import matplotlib for charts
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not installed. Chart images will be limited.")

# Try to import reportlab for PDF
try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, KeepTogether
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF export will be limited.")


def generate_forecast_report_from_data(forecast_data: list, user: dict, stats: dict, format_type: str = 'pdf') -> BytesIO:
    """
    Generate a report using the EXACT SAME data that's shown on the dashboard
    
    Args:
        forecast_data: List of forecast data from database (same as dashboard)
        user: User object with restaurant info
        stats: Dashboard stats
        format_type: 'pdf' or 'excel'
    
    Returns:
        BytesIO buffer with the report
    """
    if format_type == 'pdf':
        return _generate_pdf_report_from_data(forecast_data, user, stats)
    else:
        return _generate_excel_report_from_data(forecast_data, user, stats)


def _generate_pdf_report_from_data(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """Generate PDF report using the provided data"""
    buffer = BytesIO()
    
    # If reportlab is not available, create a proper PDF with fallback
    if not REPORTLAB_AVAILABLE:
        return _generate_fallback_pdf(forecast_data, user, stats)
    
    try:
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#4f46e5'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'ReportHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=10,
            spaceBefore=15
        )
        
        # Title
        elements.append(Paragraph("Food Forecast AI - Demand Report", title_style))
        elements.append(Paragraph(
            f"{user.get('restaurant_name', 'Restaurant')} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))
        
        # Summary Stats
        elements.append(Paragraph("Performance Summary", heading_style))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Today\'s Customers', str(stats.get('today_customers', 0))],
            ['Forecast Accuracy', f"{stats.get('forecast_accuracy', 0)}%"],
            ['Daily Waste', f"{stats.get('daily_waste', 0)}kg"],
            ['Today\'s Revenue', f"${stats.get('today_revenue', 0)}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))
        
        # Forecast Chart (if matplotlib available)
        if MATPLOTLIB_AVAILABLE:
            chart_img = _create_forecast_chart_from_data(forecast_data)
            if chart_img:
                elements.append(Paragraph("7-Day Demand Forecast", heading_style))
                from reportlab.lib.utils import ImageReader
                img = ImageReader(chart_img)
                elements.append(Image(img, width=8*inch, height=3.5*inch))
                elements.append(Spacer(1, 10))
        
        # Forecast Data Table - USING THE SAME DATA
        elements.append(Paragraph("Detailed Forecast Data", heading_style))
        
        # Prepare table data from the provided forecast_data
        table_data = [['Date', 'Day', 'Actual Sales', 'AI Forecast', 'Difference']]
        for item in forecast_data:
            actual = item.get('actual', 0) or 0
            predicted = item.get('predicted', 0) or 0
            diff = abs(actual - predicted) if actual and predicted else 0
            
            # Get day name from date
            date_str = item.get('forecast_date', '')
            try:
                date_obj = datetime.fromisoformat(date_str)
                day_name = date_obj.strftime('%a')
            except:
                day_name = item.get('day', '')
            
            table_data.append([
                date_str[:10],
                day_name,
                str(int(actual)),
                str(int(predicted)),
                str(int(diff))
            ])
        
        # Calculate column widths
        col_widths = [1.2*inch, 0.9*inch, 1.0*inch, 1.0*inch, 0.9*inch]
        forecast_table = Table(table_data, colWidths=col_widths)
        forecast_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALTERNATING', (0, 1), (-1, -1), colors.beige, colors.white),
        ]))
        elements.append(forecast_table)
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceBefore=30
        )
        elements.append(Paragraph(
            "This report was generated automatically by Food Forecast AI",
            footer_style
        ))
        
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return _generate_fallback_pdf(forecast_data, user, stats)


def _generate_fallback_pdf(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """Generate a simple valid PDF using canvas"""
    buffer = BytesIO()
    
    try:
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.setFillColorRGB(0.31, 0.27, 0.90)
        c.drawCentredString(width/2, height - 50, "Food Forecast AI - Demand Report")
        
        # Subtitle
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0.39, 0.41, 0.51)
        c.drawCentredString(width/2, height - 75, 
            f"{user.get('restaurant_name', 'Restaurant')} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        
        # Summary Section
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.12, 0.17, 0.23)
        c.drawString(50, height - 110, "Performance Summary")
        
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0, 0, 0)
        y_pos = height - 135
        stats_data = [
            f"Today's Customers: {stats.get('today_customers', 0)}",
            f"Forecast Accuracy: {stats.get('forecast_accuracy', 0)}%",
            f"Daily Waste: {stats.get('daily_waste', 0)}kg",
            f"Today's Revenue: ${stats.get('today_revenue', 0)}"
        ]
        
        for stat in stats_data:
            c.drawString(50, y_pos, stat)
            y_pos -= 20
        
        # Forecast Data Table Header - USING THE SAME DATA
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.12, 0.17, 0.23)
        c.drawString(50, y_pos - 20, "7-Day Forecast Data")
        
        # Table headers
        c.setFont("Helvetica-Bold", 10)
        headers = ['Date', 'Day', 'Actual', 'Forecast', 'Diff']
        x_positions = [50, 130, 210, 290, 370]
        y_pos = y_pos - 45
        
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_pos, header)
        
        # Table data - FROM THE PROVIDED DATA
        c.setFont("Helvetica", 9)
        y_pos -= 15
        
        for item in forecast_data:
            actual = item.get('actual', 0) or 0
            predicted = item.get('predicted', 0) or 0
            diff = abs(actual - predicted) if actual and predicted else 0
            
            # Get day name
            date_str = item.get('forecast_date', '')
            try:
                date_obj = datetime.fromisoformat(date_str)
                day_name = date_obj.strftime('%a')
            except:
                day_name = item.get('day', '')
            
            row_data = [
                date_str[:10],
                day_name,
                str(int(actual)),
                str(int(predicted)),
                str(int(diff))
            ]
            
            for i, value in enumerate(row_data):
                c.drawString(x_positions[i], y_pos, value)
            
            y_pos -= 15
            if y_pos < 50:
                c.showPage()
                y_pos = height - 50
                c.setFont("Helvetica-Bold", 10)
                for i, header in enumerate(headers):
                    c.drawString(x_positions[i], y_pos, header)
                y_pos -= 15
                c.setFont("Helvetica", 9)
        
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(width/2, 30, "Generated by Food Forecast AI")
        
        c.save()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Fallback PDF generation error: {e}")
        buffer = BytesIO()
        buffer.write(f"Error generating PDF: {str(e)}".encode())
        buffer.seek(0)
        return buffer


def _create_forecast_chart_from_data(forecast_data: list) -> BytesIO:
    """Create a matplotlib chart from the provided data"""
    if not MATPLOTLIB_AVAILABLE or not forecast_data:
        return None
    
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        
        dates = [item.get('forecast_date', '') for item in forecast_data]
        actual = [item.get('actual', 0) or 0 for item in forecast_data]
        predicted = [item.get('predicted', 0) or 0 for item in forecast_data]
        
        # Format dates for display
        display_dates = []
        for d in dates:
            try:
                date_obj = datetime.fromisoformat(d)
                display_dates.append(date_obj.strftime('%m/%d'))
            except:
                display_dates.append(d[:5])
        
        x = range(len(display_dates))
        width = 0.35
        
        # Bar chart
        bars1 = ax.bar([i - width/2 for i in x], actual, width, label='Actual Sales', 
                       color='#10b981', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], predicted, width, label='AI Forecast',
                       color='#4f46e5', alpha=0.8)
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Number of Orders', fontsize=10)
        ax.set_title('7-Day Demand Forecast vs Actual', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(display_dates)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Chart creation error: {e}")
        return None


def _generate_excel_report_from_data(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """Generate Excel report using the provided data"""
    buffer = BytesIO()
    
    try:
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet 1: Forecast Data - USING THE SAME DATA
            df = pd.DataFrame(forecast_data)
            
            # Process dates
            df['forecast_date'] = pd.to_datetime(df['forecast_date']).dt.strftime('%Y-%m-%d')
            
            # Get day names
            df['day'] = df['forecast_date'].apply(lambda x: datetime.strptime(x, '%Y-%m-%d').strftime('%a'))
            
            # Fill missing values
            df['actual'] = df['actual'].fillna(0)
            df['predicted'] = df['predicted'].fillna(0)
            df['difference'] = abs(df['actual'] - df['predicted'])
            
            # Select and order columns
            cols = ['forecast_date', 'day', 'actual', 'predicted', 'difference']
            df = df[[c for c in cols if c in df.columns]]
            df.columns = ['Date', 'Day', 'Actual Sales', 'AI Forecast', 'Difference']
            
            df.to_excel(writer, sheet_name='Forecast Data', index=False)
            
            # Sheet 2: Summary
            summary_data = [
                ['Metric', 'Value'],
                ['Restaurant', user.get('restaurant_name', 'Restaurant')],
                ['Report Generated', datetime.now().strftime('%Y-%m-%d %H:%M')],
                ['', ''],
                ['Today\'s Customers', stats.get('today_customers', 0)],
                ['Forecast Accuracy', f"{stats.get('forecast_accuracy', 0)}%"],
                ['Daily Waste', f"{stats.get('daily_waste', 0)}kg"],
                ['Today\'s Revenue', f"${stats.get('today_revenue', 0)}"],
                ['', ''],
                ['7-Day Totals', ''],
                ['Total Actual Sales', df['Actual Sales'].sum() if not df.empty else 0],
                ['Total Forecast', df['AI Forecast'].sum() if not df.empty else 0],
                ['Average Daily Forecast', df['AI Forecast'].mean() if not df.empty else 0],
            ]
            
            # Add peak day info
            if not df.empty and 'AI Forecast' in df:
                peak_idx = df['AI Forecast'].idxmax()
                summary_data.append(['Peak Day', df.loc[peak_idx, 'Date'] if peak_idx is not None else 'N/A'])
                summary_data.append(['Peak Forecast', df['AI Forecast'].max() if not df.empty else 0])
            
            summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Excel generation error: {e}")
        buffer = BytesIO()
        df = pd.DataFrame(forecast_data)
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer


def generate_forecast_report(forecast_data: list, user: dict, stats: dict, format_type: str = 'pdf') -> BytesIO:
    """
    Generate a report for the main forecast chart
    
    Args:
        forecast_data: List of forecast data from database
        user: User object with restaurant info
        stats: Dashboard stats
        format_type: 'pdf' or 'excel'
    
    Returns:
        BytesIO buffer with the report
    """
    if format_type == 'pdf':
        return _generate_pdf_report(forecast_data, user, stats)
    else:
        return _generate_excel_report(forecast_data, user, stats)


def _generate_pdf_report(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """Generate PDF report using reportlab"""
    buffer = BytesIO()
    
    # If reportlab is not available, create a proper PDF with fallback
    if not REPORTLAB_AVAILABLE:
        return _generate_fallback_pdf(forecast_data, user, stats)
    
    try:
        # Create the PDF document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(letter),
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#4f46e5'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'ReportHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=10,
            spaceBefore=15
        )
        
        # Title
        elements.append(Paragraph("Food Forecast AI - Demand Report", title_style))
        elements.append(Paragraph(
            f"{user.get('restaurant_name', 'Restaurant')} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))
        
        # Summary Stats
        elements.append(Paragraph("Performance Summary", heading_style))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Today\'s Customers', str(stats.get('today_customers', 0))],
            ['Forecast Accuracy', f"{stats.get('forecast_accuracy', 0)}%"],
            ['Daily Waste', f"{stats.get('daily_waste', 0)}kg"],
            ['Today\'s Revenue', f"${stats.get('today_revenue', 0)}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))
        
        # Forecast Chart (if matplotlib available)
        if MATPLOTLIB_AVAILABLE:
            chart_img = _create_forecast_chart(forecast_data)
            if chart_img:
                elements.append(Paragraph("7-Day Demand Forecast", heading_style))
                from reportlab.lib.utils import ImageReader
                img = ImageReader(chart_img)
                elements.append(Image(img, width=8*inch, height=3.5*inch))
                elements.append(Spacer(1, 10))
        
        # Forecast Data Table
        elements.append(Paragraph("Detailed Forecast Data", heading_style))
        
        # Prepare table data
        table_data = [['Date', 'Day', 'Actual Sales', 'AI Forecast', 'Difference']]
        for item in forecast_data:
            actual = item.get('actual', 0) or 0
            predicted = item.get('predicted', 0) or 0
            diff = abs(actual - predicted) if actual and predicted else 0
            table_data.append([
                item.get('forecast_date', '')[:10],
                item.get('day', ''),
                str(int(actual)),
                str(int(predicted)),
                str(int(diff))
            ])
        
        # Calculate column widths
        col_widths = [1.2*inch, 0.9*inch, 1.0*inch, 1.0*inch, 0.9*inch]
        forecast_table = Table(table_data, colWidths=col_widths)
        forecast_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALTERNATING', (0, 1), (-1, -1), colors.beige, colors.white),
        ]))
        elements.append(forecast_table)
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceBefore=30
        )
        elements.append(Paragraph(
            "This report was generated automatically by Food Forecast AI",
            footer_style
        ))
        
        # Build the PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return _generate_fallback_pdf(forecast_data, user, stats)


def _generate_fallback_pdf(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """
    Generate a proper PDF using canvas when reportlab has issues
    This creates a simple but valid PDF
    """
    buffer = BytesIO()
    
    try:
        # Create a simple PDF using reportlab canvas (not platypus)
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.setFillColorRGB(0.31, 0.27, 0.90)  # #4f46e5
        c.drawCentredString(width/2, height - 50, "Food Forecast AI - Demand Report")
        
        # Subtitle
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0.39, 0.41, 0.51)  # #64748b
        c.drawCentredString(width/2, height - 75, 
            f"{user.get('restaurant_name', 'Restaurant')} | Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        
        # Summary Section
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.12, 0.17, 0.23)  # #1e293b
        c.drawString(50, height - 110, "Performance Summary")
        
        # Summary stats
        c.setFont("Helvetica", 11)
        c.setFillColorRGB(0, 0, 0)
        y_pos = height - 135
        stats_data = [
            f"Today's Customers: {stats.get('today_customers', 0)}",
            f"Forecast Accuracy: {stats.get('forecast_accuracy', 0)}%",
            f"Daily Waste: {stats.get('daily_waste', 0)}kg",
            f"Today's Revenue: ${stats.get('today_revenue', 0)}"
        ]
        
        for stat in stats_data:
            c.drawString(50, y_pos, stat)
            y_pos -= 20
        
        # Forecast Data Table Header
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.12, 0.17, 0.23)
        c.drawString(50, y_pos - 20, "7-Day Forecast Data")
        
        # Table headers
        c.setFont("Helvetica-Bold", 10)
        headers = ['Date', 'Day', 'Actual', 'Forecast', 'Diff']
        x_positions = [50, 130, 210, 290, 370]
        y_pos = y_pos - 45
        
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_pos, header)
        
        # Table data
        c.setFont("Helvetica", 9)
        y_pos -= 15
        
        for item in forecast_data[:10]:  # Show all, but limit to fit page
            actual = item.get('actual', 0) or 0
            predicted = item.get('predicted', 0) or 0
            diff = abs(actual - predicted) if actual and predicted else 0
            
            row_data = [
                item.get('forecast_date', '')[:10],
                item.get('day', '')[:8],
                str(int(actual)),
                str(int(predicted)),
                str(int(diff))
            ]
            
            for i, value in enumerate(row_data):
                c.drawString(x_positions[i], y_pos, value)
            
            y_pos -= 15
            if y_pos < 50:
                # Need new page
                c.showPage()
                y_pos = height - 50
                c.setFont("Helvetica-Bold", 10)
                for i, header in enumerate(headers):
                    c.drawString(x_positions[i], y_pos, header)
                y_pos -= 15
                c.setFont("Helvetica", 9)
        
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.drawCentredString(width/2, 30, "Generated by Food Forecast AI")
        
        c.save()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Fallback PDF generation error: {e}")
        # Final fallback - return an error message as a text file
        buffer = BytesIO()
        buffer.write(f"Error generating PDF: {str(e)}".encode())
        buffer.seek(0)
        return buffer


def _create_forecast_chart(forecast_data: list) -> BytesIO:
    """Create a matplotlib chart of the forecast data"""
    if not MATPLOTLIB_AVAILABLE or not forecast_data:
        return None
    
    try:
        fig, ax = plt.subplots(figsize=(10, 4))
        
        dates = [item.get('forecast_date', '') for item in forecast_data]
        actual = [item.get('actual', 0) or 0 for item in forecast_data]
        predicted = [item.get('predicted', 0) or 0 for item in forecast_data]
        
        # Format dates for display
        display_dates = []
        for d in dates:
            try:
                date_obj = datetime.fromisoformat(d)
                display_dates.append(date_obj.strftime('%m/%d'))
            except:
                display_dates.append(d[:5])
        
        x = range(len(display_dates))
        width = 0.35
        
        # Bar chart
        bars1 = ax.bar([i - width/2 for i in x], actual, width, label='Actual Sales', 
                       color='#10b981', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], predicted, width, label='AI Forecast',
                       color='#4f46e5', alpha=0.8)
        
        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f'{int(height)}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3),
                           textcoords="offset points",
                           ha='center', va='bottom', fontsize=8)
        
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Number of Orders', fontsize=10)
        ax.set_title('7-Day Demand Forecast vs Actual', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(display_dates)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Chart creation error: {e}")
        return None


def _generate_excel_report(forecast_data: list, user: dict, stats: dict) -> BytesIO:
    """Generate Excel report"""
    buffer = BytesIO()
    
    try:
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Sheet 1: Forecast Data
            df = pd.DataFrame(forecast_data)
            df['forecast_date'] = pd.to_datetime(df['forecast_date']).dt.strftime('%Y-%m-%d')
            df['actual'] = df['actual'].fillna(0)
            df['predicted'] = df['predicted'].fillna(0)
            df['difference'] = abs(df['actual'] - df['predicted'])
            
            # Select and order columns
            cols = ['forecast_date', 'day', 'actual', 'predicted', 'difference']
            df = df[[c for c in cols if c in df.columns]]
            df.columns = ['Date', 'Day', 'Actual Sales', 'AI Forecast', 'Difference']
            
            df.to_excel(writer, sheet_name='Forecast Data', index=False)
            
            # Sheet 2: Summary
            summary_data = [
                ['Metric', 'Value'],
                ['Restaurant', user.get('restaurant_name', 'Restaurant')],
                ['Report Generated', datetime.now().strftime('%Y-%m-%d %H:%M')],
                ['', ''],
                ['Today\'s Customers', stats.get('today_customers', 0)],
                ['Forecast Accuracy', f"{stats.get('forecast_accuracy', 0)}%"],
                ['Daily Waste', f"{stats.get('daily_waste', 0)}kg"],
                ['Today\'s Revenue', f"${stats.get('today_revenue', 0)}"],
                ['', ''],
                ['7-Day Totals', ''],
                ['Total Actual Sales', df['Actual Sales'].sum() if not df.empty else 0],
                ['Total Forecast', df['AI Forecast'].sum() if not df.empty else 0],
                ['Average Daily Forecast', df['AI Forecast'].mean() if not df.empty else 0],
                ['Peak Day', df.loc[df['AI Forecast'].idxmax(), 'Date'] if not df.empty and 'AI Forecast' in df else 'N/A'],
                ['Peak Forecast', df['AI Forecast'].max() if not df.empty else 0]
            ]
            summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 30)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Excel generation error: {e}")
        # Fallback to simple CSV-like Excel
        buffer = BytesIO()
        df = pd.DataFrame(forecast_data)
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer