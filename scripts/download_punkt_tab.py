#!/usr/bin/env python
"""
Script to download the specific NLTK punkt_tab resource.
"""

import nltk
import sys
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def download_punkt_tab():
    """Download the punkt_tab resource specifically."""
    try:
        # First try the standard punkt download which might include punkt_tab
        logger.info("Downloading NLTK punkt resource")
        nltk.download('punkt')
        
        # Check if punkt_tab is now available
        try:
            import nltk.tokenize.punkt
            logger.info("Successfully loaded punkt module")
        except ImportError as e:
            logger.error(f"Failed to load punkt module: {e}")
            return False
        
        # Print NLTK data path for debugging
        nltk_data_path = nltk.data.path
        logger.info(f"NLTK data paths: {nltk_data_path}")
        
        # Check if punkt_tab file exists in any of the NLTK data paths
        punkt_tab_found = False
        for path in nltk_data_path:
            punkt_tab_path = os.path.join(path, 'tokenizers', 'punkt_tab', 'english')
            if os.path.exists(punkt_tab_path):
                logger.info(f"Found punkt_tab at: {punkt_tab_path}")
                punkt_tab_found = True
                break
        
        if not punkt_tab_found:
            logger.warning("punkt_tab not found in NLTK data paths")
            
            # Try to download punkt_tab specifically
            try:
                logger.info("Attempting to download punkt_tab specifically")
                nltk.download('punkt_tab')
                logger.info("Successfully downloaded punkt_tab")
            except Exception as e:
                logger.error(f"Failed to download punkt_tab: {e}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting NLTK punkt_tab downloader")
    
    try:
        success = download_punkt_tab()
        if success:
            logger.info("NLTK punkt resources downloaded successfully")
            sys.exit(0)
        else:
            logger.error("Failed to download NLTK punkt resources")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)