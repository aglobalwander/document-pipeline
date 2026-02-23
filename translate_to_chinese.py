#!/usr/bin/env python3
"""
Translate text file to Chinese using DeepL API
"""

import os
import sys
import deepl
from pathlib import Path
import argparse
from dotenv import load_dotenv

# Load environment variables from centralized API key store
MASTER_ENV_PATH = Path.home() / ".config" / "api-keys" / ".env.master"
if MASTER_ENV_PATH.exists():
    load_dotenv(dotenv_path=MASTER_ENV_PATH, override=False)

def translate_text_file(input_path, output_path, api_key, target_lang='ZH'):
    """
    Translate a text file using DeepL API

    Args:
        input_path: Path to input text file
        output_path: Path to output translated file
        api_key: DeepL API key
        target_lang: Target language code (default: ZH for Chinese)
    """
    # Initialize DeepL translator
    translator = deepl.Translator(api_key)

    # Read the input file
    print(f"Reading file: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Check text length
    text_length = len(text)
    print(f"Text length: {text_length} characters")

    # Split text into chunks if it's too long (DeepL has a limit)
    max_chunk_size = 50000  # DeepL's limit per request

    if text_length > max_chunk_size:
        print(f"Text is too long, splitting into chunks...")
        chunks = []
        words = text.split('\n\n')  # Split by paragraphs
        current_chunk = ""

        for paragraph in words:
            if len(current_chunk) + len(paragraph) + 2 < max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"

        if current_chunk:
            chunks.append(current_chunk.strip())

        print(f"Split into {len(chunks)} chunks")

        # Translate each chunk
        translated_chunks = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Translating chunk {i}/{len(chunks)}...")
            try:
                result = translator.translate_text(
                    chunk,
                    target_lang=target_lang,
                    preserve_formatting=True
                )
                translated_chunks.append(result.text)
            except Exception as e:
                print(f"Error translating chunk {i}: {e}")
                raise

        # Combine translated chunks
        translated_text = "\n\n".join(translated_chunks)
    else:
        # Translate the entire text at once
        print("Translating text...")
        try:
            result = translator.translate_text(
                text,
                target_lang=target_lang,
                preserve_formatting=True
            )
            translated_text = result.text
        except Exception as e:
            print(f"Error translating: {e}")
            raise

    # Save the translated text
    print(f"Saving translated text to: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(translated_text)

    print("Translation completed successfully!")

    # Check usage if available
    try:
        usage = translator.get_usage()
        if usage.character.limit:
            print(f"DeepL API usage: {usage.character.count}/{usage.character.limit} characters")
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description='Translate text file to Chinese using DeepL API')
    parser.add_argument('--input', '-i', type=str,
                       default='/Users/scottwilliams/Development/master_projects/pipeline-documents/data/input/text/belonging.txt',
                       help='Input text file path')
    parser.add_argument('--output', '-o', type=str,
                       default=None,
                       help='Output file path (default: input_chinese.txt)')
    parser.add_argument('--api-key', '-k', type=str,
                       default=None,
                       help='DeepL API key (or set DEEPL_API_KEY env variable)')
    parser.add_argument('--target-lang', '-t', type=str,
                       default='ZH',
                       help='Target language code (default: ZH for Chinese)')

    args = parser.parse_args()

    # Get API key from arguments or environment variable
    api_key = args.api_key or os.environ.get('DEEPL_API_KEY')

    if not api_key:
        print("Error: DeepL API key is required!")
        print("Please provide it via --api-key argument or set DEEPL_API_KEY environment variable")
        sys.exit(1)

    # Set default output path if not provided
    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        # Create output path in the output directory
        output_dir = Path('/Users/scottwilliams/Development/master_projects/pipeline-documents/data/output/text')
        output_path = output_dir / f"{input_path.stem}_chinese.txt"

    # Check if input file exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Perform translation
    try:
        translate_text_file(input_path, output_path, api_key, args.target_lang)
    except Exception as e:
        print(f"Translation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
