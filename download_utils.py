"""
download_utils.py - Handles downloads for forecasts
"""

import io
import pandas as pd
from datetime import datetime
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Try to import matplotlib for PNG
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not installed. PNG export unavailable.")

# Try to import reportlab for PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed. PDF export will be limited.")


def download_forecast_pdf(forecast_data: dict) -> BytesIO:
    """Generate PDF report"""
    buffer = BytesIO()
    
    if not REPORTLAB_AVAILABLE:
        # Fallback: Simple text PDF
        content = []
    
        content.append("""
        ====================================
        DEMAND FORECAST REPORT
        ====================================
    
        """)
    
        content.append(f"""
        Item: {forecast_data.get('meal_id', 'Unknown')}
        Category: {forecast_data.get('category', 'Unknown')}
        Cuisine: {forecast_data.get('cuisine', 'Unknown')}
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
        SUMMARY:
        - Total Demand: {forecast_data.get('summary', {}).get('total_demand', 0)}
        - Avg Daily: {forecast_data.get('summary', {}).get('avg_daily_demand', 0)}
        - Peak Day: {forecast_data.get('summary', {}).get('peak_day', 'N/A')}
        - Weekend Avg: {forecast_data.get('summary', {}).get('weekend_avg', 0)}
    
        DAILY FORECAST:
        """)
    
        for f in forecast_data.get('forecasts', []):
            content.append(f"""
        {f['date']} ({f['day']}):
            Predicted: {f['predicted_demand']}
            Range: {f['confidence_lower']} - {f['confidence_upper']}
        """)
    
        content.append("""
        ====================================
        Food Forecast AI
        ====================================
        """)
    
        # Join all content and encode once
        buffer.write(''.join(content).encode())
        buffer.seek(0)
        return buffer
    
    try:
        # Create PDF with reportlab
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#4f46e5'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        elements.append(Paragraph("Demand Forecast Report", title_style))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=30
        )
        elements.append(Paragraph(
            f"Item {forecast_data.get('meal_id', 'Unknown')} | "
            f"{forecast_data.get('category', 'Unknown')} | "
            f"{forecast_data.get('cuisine', 'Unknown')}",
            subtitle_style
        ))
        
        # Summary
        summary = forecast_data.get('summary', {})
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8
        )
        elements.append(Paragraph(f"""
            <b>Forecast Summary</b><br/>
            Total Demand: {summary.get('total_demand', 0)} | 
            Avg Daily: {summary.get('avg_daily_demand', 0)} | 
            Peak Day: {summary.get('peak_day', 'N/A')}
        """, summary_style))
        elements.append(Spacer(1, 10))
        
        # Table
        forecasts = forecast_data.get('forecasts', [])
        if forecasts:
            table_data = [['Date', 'Day', 'Predicted', 'Lower', 'Upper']]
            for f in forecasts:
                table_data.append([
                    f['date'],
                    f['day'],
                    str(f['predicted_demand']),
                    str(f['confidence_lower']),
                    str(f['confidence_upper'])
                ])
            
            table = Table(table_data, colWidths=[1.2*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(table)
        
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
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Food Forecast AI",
            footer_style
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        # Fallback to simple text
        buffer = BytesIO()
        buffer.write(f"Error generating PDF: {str(e)}".encode())
        buffer.seek(0)
        return buffer


def download_forecast_excel(forecast_data: dict) -> BytesIO:
    """Generate Excel file"""
    buffer = BytesIO()
    
    try:
        forecasts = forecast_data.get('forecasts', [])
        
        if forecasts:
            # Create DataFrame
            df = pd.DataFrame(forecasts)
            cols = ['date', 'day', 'predicted_demand', 'confidence_lower', 'confidence_upper']
            df = df[[c for c in cols if c in df.columns]]
            
            # Write to Excel
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Forecast', index=False)
                
                # Summary sheet
                summary = forecast_data.get('summary', {})
                summary_data = [
                    ['Metric', 'Value'],
                    ['Item ID', forecast_data.get('meal_id', 'Unknown')],
                    ['Category', forecast_data.get('category', 'Unknown')],
                    ['Cuisine', forecast_data.get('cuisine', 'Unknown')],
                    ['Total Demand', summary.get('total_demand', 0)],
                    ['Avg Daily', summary.get('avg_daily_demand', 0)],
                    ['Peak Day', summary.get('peak_day', 'N/A')],
                    ['Peak Date', summary.get('peak_date', 'N/A')],
                    ['Weekend Avg', summary.get('weekend_avg', 0)],
                    ['Weekday Avg', summary.get('weekday_avg', 0)]
                ]
                summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Excel generation error: {e}")
        buffer = BytesIO()
        buffer.write(f"Error generating Excel: {str(e)}".encode())
        buffer.seek(0)
        return buffer


def download_forecast_png(forecast_data: dict) -> BytesIO:
    """Generate PNG chart"""
    buffer = BytesIO()
    
    if not MATPLOTLIB_AVAILABLE:
        buffer.write(b"matplotlib not installed. Please install: pip install matplotlib")
        buffer.seek(0)
        return buffer
    
    try:
        forecasts = forecast_data.get('forecasts', [])
        
        if not forecasts:
            buffer.write(b"No forecast data available")
            buffer.seek(0)
            return buffer
        
        dates = [f['date'] for f in forecasts]
        demands = [f['predicted_demand'] for f in forecasts]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(dates, demands, color='#4f46e5', alpha=0.7)
        
        # Add value labels
        for bar, value in zip(bars, demands):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                   str(value), ha='center', va='bottom', fontsize=9)
        
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Predicted Demand', fontsize=12)
        ax.set_title(f"7-Day Demand Forecast - Item {forecast_data.get('meal_id', '')}", 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"PNG generation error: {e}")
        buffer = BytesIO()
        buffer.write(f"Error generating chart: {str(e)}".encode())
        buffer.seek(0)
        return buffer