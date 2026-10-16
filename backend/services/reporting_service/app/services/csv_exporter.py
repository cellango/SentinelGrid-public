"""
CSV Exporter
Exports compliance report data to CSV format
"""

import logging
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CSVExporter:
    """Export report data to CSV format."""
    
    def export_table(
        self,
        data: List[Dict[str, Any]],
        output_path: str,
        columns: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Export data table to CSV.
        
        Args:
            data: List of dictionaries with table data
            output_path: Path to save CSV file
            columns: Optional list of columns to export (in order)
            headers: Optional dict mapping column names to display headers
            
        Returns:
            Path to generated CSV file
        """
        if not data:
            logger.warning("No data to export")
            return output_path
        
        # Determine columns if not provided
        if columns is None:
            columns = list(data[0].keys())
        
        # Determine headers
        if headers is None:
            headers = {col: col.replace('_', ' ').title() for col in columns}
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                # Write header
                writer = csv.writer(csvfile)
                writer.writerow([headers.get(col, col) for col in columns])
                
                # Write data
                for row in data:
                    writer.writerow([
                        self._format_value(row.get(col, ''))
                        for col in columns
                    ])
            
            logger.info(f"CSV exported successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}", exc_info=True)
            raise
    
    def export_to_string(
        self,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Export data table to CSV string.
        
        Args:
            data: List of dictionaries with table data
            columns: Optional list of columns to export (in order)
            headers: Optional dict mapping column names to display headers
            
        Returns:
            CSV content as string
        """
        if not data:
            return ""
        
        # Determine columns if not provided
        if columns is None:
            columns = list(data[0].keys())
        
        # Determine headers
        if headers is None:
            headers = {col: col.replace('_', ' ').title() for col in columns}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([headers.get(col, col) for col in columns])
        
        # Write data
        for row in data:
            writer.writerow([
                self._format_value(row.get(col, ''))
                for col in columns
            ])
        
        return output.getvalue()
    
    def export_multiple_tables(
        self,
        tables: Dict[str, List[Dict[str, Any]]],
        output_path: str
    ) -> str:
        """
        Export multiple tables to a single CSV file with section headers.
        
        Args:
            tables: Dict of table_name -> data
            output_path: Path to save CSV file
            
        Returns:
            Path to generated CSV file
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                for i, (table_name, data) in enumerate(tables.items()):
                    # Add spacing between tables
                    if i > 0:
                        writer.writerow([])
                        writer.writerow([])
                    
                    # Write table header
                    writer.writerow([f"=== {table_name} ==="])
                    writer.writerow([])
                    
                    # Write table data
                    if data:
                        columns = list(data[0].keys())
                        headers = [col.replace('_', ' ').title() for col in columns]
                        writer.writerow(headers)
                        
                        for row in data:
                            writer.writerow([
                                self._format_value(row.get(col, ''))
                                for col in columns
                            ])
            
            logger.info(f"Multi-table CSV exported successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to export multi-table CSV: {e}", exc_info=True)
            raise
    
    def _format_value(self, value: Any) -> str:
        """Format value for CSV export."""
        if value is None:
            return ""
        elif isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, (list, dict)):
            return str(value)
        else:
            return str(value)


# Singleton
_csv_exporter: Optional[CSVExporter] = None


def get_csv_exporter() -> CSVExporter:
    """Get or create the global CSV exporter instance."""
    global _csv_exporter
    if _csv_exporter is None:
        _csv_exporter = CSVExporter()
    return _csv_exporter

