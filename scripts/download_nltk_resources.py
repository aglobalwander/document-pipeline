#!/usr/bin/env python
"""
Script to download required NLTK resources for the document pipeline.
"""

import nltk
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def download_nltk_resources():
    """Download all required NLTK resources for the document pipeline."""
    resources = [
        'punkt',        # For sentence tokenization
        'stopwords',    # Common stopwords
        'wordnet',      # For lemmatization
        'averaged_perceptron_tagger'  # For POS tagging
    ]
    
    success = True
    for resource in resources:
        try:
            logger.info(f"Downloading NLTK resource: {resource}")
            nltk.download(resource)
            logger.info(f"Successfully downloaded {resource}")
        except Exception as e:
            logger.error(f"Failed to download {resource}: {e}")
            success = False
    
    return success

if __name__ == "__main__":
    logger.info("Starting NLTK resource downloader")
    
    try:
        success = download_nltk_resources()
        if success:
            logger.info("All NLTK resources downloaded successfully")
            sys.exit(0)
        else:
            logger.error("Some NLTK resources failed to download")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)