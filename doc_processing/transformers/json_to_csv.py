"""Transform JSON data to CSV format."""
import os
import csv
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List

from doc_processing.embedding.base import PipelineComponent
from doc_processing.embedding.base import BaseTransformer
from doc_processing.config import get_settings

class JsonToCSV(BaseTransformer, PipelineComponent):
    """Transform JSON data to CSV format."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the JSON to CSV transformer.
        
        Args:
            config: Configuration options
                merge_csv: Whether to merge multiple CSV outputs into a single file
        """
        super().__init__(config or {})
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        self.merge_csv = self.config.get('merge_csv', False)
        self.logger.info(f"Initialized JsonToCSV transformer (merge_csv={self.merge_csv})")

    def transform(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Transform JSON data to CSV.
        
        Args:
            document: Document dictionary with content field containing JSON data
            
        Returns:
            Processed document with CSV output paths
        """
        if not document.get('content'):
            self.logger.error("No content field in document")
            return document
            
        # Get the input path from metadata if available
        input_path = document.get('metadata', {}).get('input_path', '')
        if not input_path:
            self.logger.warning("No input_path in metadata, using generic filename")
            input_path = "data.json"
            
        # Create output directory
        output_dir = Path(self.settings.output_dir) / "csv"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        input_filename = Path(input_path).stem
        output_path = output_dir / f"{input_filename}.csv"
        
        try:
            # Parse JSON content
            if isinstance(document['content'], str):
                try:
                    json_data = json.loads(document['content'])
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse JSON content")
                    return document
            else:
                json_data = document['content']
                
            # Convert JSON to DataFrame
            df = self._json_to_dataframe(json_data)
            
            # Save to CSV
            csv_paths = self._save_to_csv(df, output_path, input_filename)
            
            # Update document
            result = document.copy()
            result['csv_paths'] = csv_paths
            result['metadata'] = document.get('metadata', {})
            result['metadata']['csv_output'] = csv_paths
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error converting JSON to CSV: {e}")
            return document

    def _json_to_dataframe(self, json_data: Any) -> pd.DataFrame:
        """Convert JSON data to pandas DataFrame.
        
        Args:
            json_data: JSON data (dict, list, or other JSON-serializable object)
            
        Returns:
            pandas DataFrame
        """
        # Handle different JSON structures
        if isinstance(json_data, list):
            # List of objects/records
            return pd.json_normalize(json_data)
        elif isinstance(json_data, dict):
            # Single object or nested structure
            # Flatten one level of nesting
            flattened = {}
            for key, value in json_data.items():
                if isinstance(value, dict):
                    # Flatten nested dict with dot notation
                    for subkey, subvalue in value.items():
                        flattened[f"{key}.{subkey}"] = subvalue
                else:
                    flattened[key] = value
            return pd.DataFrame([flattened])
        else:
            # Scalar value or other type
            self.logger.warning(f"Unexpected JSON structure: {type(json_data)}")
            return pd.DataFrame([{"value": json_data}])

    def _save_to_csv(self, df: pd.DataFrame, output_path: Path, input_filename: str) -> List[str]:
        """Save DataFrame to CSV file(s).
        
        Args:
            df: pandas DataFrame
            output_path: Path to save the CSV file
            input_filename: Original input filename (without extension)
            
        Returns:
            List of CSV file paths
        """
        csv_paths = []
        
        # Check if the DataFrame is empty
        if df.empty:
            self.logger.warning("Empty DataFrame, no CSV file created")
            return csv_paths
            
        # Handle nested structures by creating multiple CSV files
        if any(isinstance(val, (list, dict)) for val in df.values.flatten() if val is not None):
            # Create a CSV file for each column with nested data
            for col in df.columns:
                if any(isinstance(val, (list, dict)) for val in df[col] if val is not None):
                    # Create a separate CSV for this column
                    col_df = pd.json_normalize(df[col].tolist())
                    col_path = output_path.parent / f"{input_filename}_{col}.csv"
                    col_df.to_csv(col_path, index=False)
                    csv_paths.append(str(col_path))
            
            # Create a CSV for the non-nested columns
            simple_cols = [col for col in df.columns 
                          if not any(isinstance(val, (list, dict)) for val in df[col] if val is not None)]
            if simple_cols:
                simple_df = df[simple_cols]
                simple_df.to_csv(output_path, index=False)
                csv_paths.append(str(output_path))
        else:
            # Save the entire DataFrame to a single CSV
            df.to_csv(output_path, index=False)
            csv_paths.append(str(output_path))
            
        # Merge CSV files if requested
        if self.merge_csv and len(csv_paths) > 1:
            merged_path = output_path.parent / f"{input_filename}_merged.csv"
            self._merge_csv_files(csv_paths, merged_path)
            csv_paths.append(str(merged_path))
            
        return csv_paths

    def _merge_csv_files(self, csv_paths: List[str], output_path: Path) -> None:
        """Merge multiple CSV files into a single file.
        
        Args:
            csv_paths: List of CSV file paths
            output_path: Path to save the merged CSV file
        """
        try:
            # Read all CSV files
            dfs = []
            for path in csv_paths:
                df = pd.read_csv(path)
                # Add filename as a column to identify the source
                filename = Path(path).stem
                df['source'] = filename
                dfs.append(df)
                
            # Concatenate all DataFrames
            if dfs:
                merged_df = pd.concat(dfs, ignore_index=True)
                merged_df.to_csv(output_path, index=False)
                self.logger.info(f"Merged {len(dfs)} CSV files into {output_path}")
            else:
                self.logger.warning("No CSV files to merge")
                
        except Exception as e:
            self.logger.error(f"Error merging CSV files: {e}")