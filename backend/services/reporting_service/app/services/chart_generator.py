"""
Chart Generator
Creates professional charts for compliance reports
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import io
import base64

logger = logging.getLogger(__name__)

# Try importing matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-GUI backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("Matplotlib not available, chart generation will be disabled")
    MATPLOTLIB_AVAILABLE = False


class ChartGenerator:
    """Generate charts for compliance reports."""
    
    def __init__(self):
        """Initialize chart generator."""
        if MATPLOTLIB_AVAILABLE:
            # Set professional style
            plt.style.use('seaborn-v0_8-darkgrid')
            
            # Set default colors (professional blue/gray palette)
            self.colors = {
                'primary': '#1E40AF',
                'success': '#10B981',
                'warning': '#F59E0B',
                'danger': '#EF4444',
                'info': '#3B82F6',
                'secondary': '#64748B'
            }
    
    def generate_bar_chart(
        self,
        data: Dict[str, float],
        title: str,
        xlabel: str = '',
        ylabel: str = '',
        color: str = 'primary',
        output_format: str = 'png'
    ) -> str:
        """
        Generate bar chart.
        
        Args:
            data: Dictionary of label -> value
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            color: Color key from self.colors
            output_format: 'png' or 'base64'
            
        Returns:
            File path or base64 encoded image
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("Matplotlib not available")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = list(data.keys())
        values = list(data.values())
        
        ax.bar(labels, values, color=self.colors.get(color, self.colors['primary']))
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        
        # Rotate x-axis labels if many items
        if len(labels) > 5:
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Return as base64 or save
        if output_format == 'base64':
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return f"data:image/png;base64,{image_base64}"
        else:
            output_path = f"/tmp/chart_{title.replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return output_path
    
    def generate_pie_chart(
        self,
        data: Dict[str, float],
        title: str,
        output_format: str = 'png'
    ) -> str:
        """Generate pie chart."""
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("Matplotlib not available")
        
        fig, ax = plt.subplots(figsize=(8, 8))
        
        labels = list(data.keys())
        values = list(data.values())
        
        colors = [self.colors['primary'], self.colors['success'], 
                  self.colors['warning'], self.colors['danger'],
                  self.colors['info'], self.colors['secondary']]
        
        ax.pie(values, labels=labels, autopct='%1.1f%%', 
               colors=colors[:len(labels)], startangle=90)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if output_format == 'base64':
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return f"data:image/png;base64,{image_base64}"
        else:
            output_path = f"/tmp/chart_{title.replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return output_path
    
    def generate_line_chart(
        self,
        data: Dict[str, List[float]],
        title: str,
        xlabel: str = '',
        ylabel: str = '',
        x_labels: Optional[List[str]] = None,
        output_format: str = 'png'
    ) -> str:
        """
        Generate line chart.
        
        Args:
            data: Dictionary of series_name -> values list
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            x_labels: Labels for X-axis points
            output_format: 'png' or 'base64'
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("Matplotlib not available")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        colors = list(self.colors.values())
        
        for i, (series_name, values) in enumerate(data.items()):
            if x_labels:
                ax.plot(x_labels, values, marker='o', 
                       label=series_name, color=colors[i % len(colors)])
            else:
                ax.plot(values, marker='o', 
                       label=series_name, color=colors[i % len(colors)])
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_format == 'base64':
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return f"data:image/png;base64,{image_base64}"
        else:
            output_path = f"/tmp/chart_{title.replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return output_path
    
    def generate_gauge_chart(
        self,
        value: float,
        title: str,
        max_value: float = 100,
        thresholds: Optional[Dict[str, Tuple[float, str]]] = None,
        output_format: str = 'png'
    ) -> str:
        """
        Generate gauge/meter chart (for compliance scores).
        
        Args:
            value: Current value
            title: Chart title
            max_value: Maximum value on gauge
            thresholds: Dict of level -> (threshold, color_key)
            output_format: 'png' or 'base64'
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("Matplotlib not available")
        
        if thresholds is None:
            thresholds = {
                'critical': (40, 'danger'),
                'warning': (70, 'warning'),
                'good': (90, 'success'),
                'excellent': (100, 'success')
            }
        
        # Determine color based on value
        color = self.colors['secondary']
        for level, (threshold, color_key) in sorted(thresholds.items(), key=lambda x: x[1][0]):
            if value <= threshold:
                color = self.colors[color_key]
                break
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        # Draw gauge
        ax.barh([0], [value], color=color, height=0.5)
        ax.barh([0], [max_value - value], left=[value], 
                color='#E5E7EB', height=0.5)
        
        ax.set_xlim(0, max_value)
        ax.set_ylim(-0.5, 0.5)
        ax.set_xticks([0, max_value/4, max_value/2, 3*max_value/4, max_value])
        ax.set_yticks([])
        
        # Add value text
        ax.text(value/2, 0, f'{value:.1f}', 
                ha='center', va='center', fontsize=20, fontweight='bold')
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        
        if output_format == 'base64':
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)
            return f"data:image/png;base64,{image_base64}"
        else:
            output_path = f"/tmp/chart_{title.replace(' ', '_')}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return output_path


# Singleton
_chart_generator: Optional[ChartGenerator] = None


def get_chart_generator() -> ChartGenerator:
    """Get or create the global chart generator instance."""
    global _chart_generator
    if _chart_generator is None:
        _chart_generator = ChartGenerator()
    return _chart_generator

