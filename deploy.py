#!/usr/bin/env python3
"""
Deploy script for GitHub Pages

This script deploys the static site generated in treepics-map/output/site/
to the gh-pages branch for GitHub Pages hosting.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd, check=True, capture_output=False):
    """Run a shell command and handle errors."""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=isinstance(cmd, str), 
                                  capture_output=True, text=True, check=check)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=isinstance(cmd, str), check=check)
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if capture_output and e.stdout:
            print(f"stdout: {e.stdout}")
        if capture_output and e.stderr:
            print(f"stderr: {e.stderr}")
        sys.exit(1)


def check_git_repo():
    """Ensure we're in a git repository."""
    if not Path('.git').exists():
        print("Error: Not in a git repository")
        sys.exit(1)


def check_source_directory():
    """Ensure the source directory exists and has content."""
    source_dir = Path('treepics-map/output/site')
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        print("Please run treepics-map/main.py to generate the site first")
        sys.exit(1)
    
    index_file = source_dir / 'index.html'
    if not index_file.exists():
        print(f"Error: {index_file} not found in source directory")
        print("Please ensure the site is properly generated")
        sys.exit(1)
    
    return source_dir


def get_current_branch():
    """Get the current git branch name."""
    return run_command(['git', 'branch', '--show-current'], capture_output=True)


def branch_exists(branch_name):
    """Check if a git branch exists locally."""
    try:
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], 
                   check=False, capture_output=True)
        return True
    except:
        return False


def remote_branch_exists(branch_name):
    """Check if a git branch exists on origin."""
    try:
        run_command(['git', 'show-ref', '--verify', '--quiet', f'refs/remotes/origin/{branch_name}'], 
                   check=False, capture_output=True)
        return True
    except:
        return False


def deploy():
    """Main deployment function."""
    print("Starting GitHub Pages deployment...")
    
    # Validate environment
    check_git_repo()
    source_dir = check_source_directory()
    current_branch = get_current_branch()
    
    print(f"Current branch: {current_branch}")
    print(f"Source directory: {source_dir}")
    
    # Ensure we have a clean working directory
    status = run_command(['git', 'status', '--porcelain'], capture_output=True)
    if status:
        print("Error: Working directory is not clean:")
        print(status)
        print("Please commit or stash your changes before deploying.")
        sys.exit(1)
    
    # Copy site contents to a temporary directory first
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"Copying site contents to temporary directory...")
        for item in source_dir.iterdir():
            dest = temp_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # Fetch latest changes from remote
        print("Fetching latest changes from remote...")
        run_command(['git', 'fetch', 'origin'])
        
        # Switch to gh-pages branch and reset to clean state
        if branch_exists('gh-pages'):
            print("Switching to existing gh-pages branch...")
            run_command(['git', 'checkout', 'gh-pages'])
            
            # Reset to remote if it exists to get a clean state
            if remote_branch_exists('gh-pages'):
                print("Resetting to origin/gh-pages...")
                run_command(['git', 'reset', '--hard', 'origin/gh-pages'])
                
            # Clean the gh-pages branch (remove all files except .git)
            print("Cleaning gh-pages branch...")
            for item in Path('.').iterdir():
                if item.name == '.git':
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
        else:
            print("Creating new gh-pages branch...")
            if remote_branch_exists('gh-pages'):
                # Create local branch tracking remote
                run_command(['git', 'checkout', '-b', 'gh-pages', 'origin/gh-pages'])
                # Clean the branch
                print("Cleaning gh-pages branch...")
                for item in Path('.').iterdir():
                    if item.name == '.git':
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            else:
                # Create orphan branch (no history)
                run_command(['git', 'checkout', '--orphan', 'gh-pages'])
        
        # Copy site contents from temp to root
        print(f"Copying site contents from temporary directory to gh-pages...")
        for item in temp_path.iterdir():
            dest = Path('.') / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
    
    # Verify index.html exists at root
    if not Path('index.html').exists():
        print("Error: index.html not found at root after copying")
        sys.exit(1)
    
    print("Site contents copied successfully!")
    
    # Add all files to git
    run_command(['git', 'add', '.'])
    
    # Debug: Check git status
    print("Git status after adding files:")
    run_command(['git', 'status', '--porcelain'])
    
    # Check if there are changes to commit
    try:
        run_command(['git', 'diff', '--staged', '--quiet'], check=False)
        print("No changes to commit - site is already up to date")
        has_changes = False
    except subprocess.CalledProcessError:
        # There are changes to commit
        has_changes = True
        print("Changes detected for commit")
    
    if has_changes:
        print("Committing changes...")
        run_command(['git', 'commit', '-m', f'Deploy site from {current_branch} to GitHub Pages'])
        
        # Push to origin
        print("Pushing to origin/gh-pages...")
        run_command(['git', 'push', 'origin', 'gh-pages'])
        
        print("✅ Successfully deployed to GitHub Pages!")
    else:
        print("No changes detected - resetting staged files")
    
    # Always ensure working directory is clean before switching branches
    # This handles the case where files were added but no commit was needed
    print("Cleaning working directory...")
    run_command(['git', 'reset', '--hard', 'HEAD'])
    
    # Switch back to original branch
    print(f"Switching back to {current_branch}...")
    run_command(['git', 'checkout', current_branch])
    
    print("🚀 Deployment complete!")
    print("Your site should be available at: https://seth127.github.io/treepics")


if __name__ == '__main__':
    try:
        deploy()
    except KeyboardInterrupt:
        print("\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(1)