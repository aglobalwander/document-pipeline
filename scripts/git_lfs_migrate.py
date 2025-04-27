#!/usr/bin/env python3
"""
Git LFS Migration Script

This script identifies files larger than a specified size threshold (default: 5MB)
and automatically migrates them to Git LFS.

Usage:
    python scripts/git_lfs_migrate.py [--threshold THRESHOLD_MB] [--dry-run]

Options:
    --threshold THRESHOLD_MB  Size threshold in MB (default: 5)
    --dry-run                 Show what would be done without making changes
    --help                    Show this help message and exit
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def get_file_size_mb(file_path):
    """Get file size in megabytes."""
    return os.path.getsize(file_path) / (1024 * 1024)


def check_git_lfs_installed():
    """Check if Git LFS is installed."""
    try:
        subprocess.run(
            ["git", "lfs", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def setup_git_lfs():
    """Set up Git LFS if not already set up."""
    try:
        # Check if Git LFS is already set up in the repository
        result = subprocess.run(
            ["git", "lfs", "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        if "Not in a Git repository" in result.stderr:
            print("Error: Not in a Git repository.")
            return False
            
        if "Git LFS is not initialized" in result.stderr:
            print("Initializing Git LFS...")
            subprocess.run(["git", "lfs", "install"], check=True)
            return True
            
        return True
    except subprocess.SubprocessError as e:
        print(f"Error setting up Git LFS: {e}")
        return False


def is_file_tracked_by_lfs(file_path):
    """Check if a file is already tracked by Git LFS."""
    try:
        result = subprocess.run(
            ["git", "check-attr", "filter", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return "lfs" in result.stdout
    except subprocess.SubprocessError:
        return False


def find_large_files(threshold_mb, exclude_patterns=None):
    """Find all files larger than threshold_mb."""
    if exclude_patterns is None:
        exclude_patterns = [".git/", "node_modules/", "__pycache__/", "*.pyc"]
    
    large_files = []
    
    # Get the repository root directory
    try:
        repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.SubprocessError:
        print("Error: Not in a Git repository.")
        return []
    
    # Walk through the repository
    for root, dirs, files in os.walk(repo_root):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not any(pattern in f"{d}/" for pattern in exclude_patterns)]
        
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip excluded files
            if any(pattern in file_path for pattern in exclude_patterns):
                continue
                
            # Check if the file is in .gitignore
            try:
                check_ignored = subprocess.run(
                    ["git", "check-ignore", file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if check_ignored.returncode == 0:  # File is ignored
                    continue
            except subprocess.SubprocessError:
                pass
                
            # Check if the file is tracked by Git
            try:
                check_tracked = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if check_tracked.returncode != 0:  # File is not tracked
                    continue
            except subprocess.SubprocessError:
                continue
                
            # Check file size
            try:
                size_mb = get_file_size_mb(file_path)
                if size_mb >= threshold_mb:
                    large_files.append((file_path, size_mb))
            except (OSError, IOError):
                continue
                
    return large_files


def migrate_to_lfs(file_path, dry_run=False):
    """Migrate a file to Git LFS."""
    if is_file_tracked_by_lfs(file_path):
        return False, "Already tracked by LFS"
        
    try:
        if dry_run:
            return True, "Would migrate to LFS (dry run)"
            
        # Add the file pattern to Git LFS tracking
        file_ext = os.path.splitext(file_path)[1]
        if file_ext:
            # Track by extension if it has one
            subprocess.run(["git", "lfs", "track", f"*{file_ext}"], check=True)
        else:
            # Track the specific file if it has no extension
            subprocess.run(["git", "lfs", "track", os.path.basename(file_path)], check=True)
            
        # Make sure .gitattributes is added to git
        subprocess.run(["git", "add", ".gitattributes"], check=True)
        
        # Remove the file from Git's index
        subprocess.run(["git", "rm", "--cached", file_path], check=True)
        
        # Add the file back, now it should be tracked by LFS
        subprocess.run(["git", "add", file_path], check=True)
        
        return True, "Successfully migrated to LFS"
    except subprocess.SubprocessError as e:
        return False, f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Find and migrate large files to Git LFS")
    parser.add_argument(
        "--threshold",
        type=float,
        default=5.0,
        help="Size threshold in MB (default: 5.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Check if Git LFS is installed
    if not check_git_lfs_installed():
        print("Error: Git LFS is not installed. Please install it first.")
        print("Installation instructions: https://git-lfs.github.com/")
        return 1
        
    # Set up Git LFS
    if not args.dry_run and not setup_git_lfs():
        print("Failed to set up Git LFS. Exiting.")
        return 1
        
    # Find large files
    print(f"Finding files larger than {args.threshold} MB...")
    large_files = find_large_files(args.threshold)
    
    if not large_files:
        print("No large files found.")
        return 0
        
    # Print summary of large files
    print(f"\nFound {len(large_files)} large files:")
    for file_path, size_mb in sorted(large_files, key=lambda x: x[1], reverse=True):
        print(f"{size_mb:.2f} MB: {file_path}")
        
    # Migrate files to LFS
    if args.dry_run:
        print("\nDry run - no changes will be made.")
    else:
        print("\nMigrating files to Git LFS...")
        
    results = []
    for file_path, size_mb in large_files:
        success, message = migrate_to_lfs(file_path, args.dry_run)
        results.append((file_path, size_mb, success, message))
        
    # Print migration results
    print("\nMigration results:")
    for file_path, size_mb, success, message in results:
        status = "SUCCESS" if success else "FAILED"
        print(f"{status}: {size_mb:.2f} MB: {file_path} - {message}")
        
    # Print summary
    successful = sum(1 for _, _, success, _ in results if success)
    print(f"\nSummary: {successful}/{len(results)} files migrated to Git LFS.")
    
    if not args.dry_run and successful > 0:
        print("\nNext steps:")
        print("1. Review the changes with 'git status'")
        print("2. Commit the changes with 'git commit -m \"Migrate large files to Git LFS\"'")
        
    return 0


if __name__ == "__main__":
    sys.exit(main())