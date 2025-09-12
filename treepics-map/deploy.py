#!/usr/bin/env python3
"""
Deployment script for TreePics Map to GitHub Pages.

This script:
1. Builds the static site locally (with your photos)
2. Creates/updates a gh-pages branch with only the generated site
3. Pushes to GitHub Pages without committing source photos

Usage:
    python deploy.py
"""

import subprocess
import shutil
import os
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and handle errors."""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def main():
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    print("🌳 TreePics Map - GitHub Pages Deployment")
    print("=" * 50)
    
    # Step 1: Build the site
    print("📸 Step 1: Building the static site...")
    print("💡 Note: Make sure you've run 'python convert_photos.py' first")
    run_command("uv run python main.py")
    print("✅ Site built successfully!")
    
    # Check if site was generated
    site_dir = Path("output/site")
    if not site_dir.exists():
        print("❌ Error: Site directory not found. Build may have failed.")
        sys.exit(1)
    
    # Step 2: Check git status
    print("\n🔍 Step 2: Checking git status...")
    current_branch = run_command("git branch --show-current")
    print(f"Current branch: {current_branch}")
    
    # Make sure we have no uncommitted changes to important files
    status = run_command("git status --porcelain")
    important_changes = [line for line in status.split('\n') if line and 
                        not any(pattern in line for pattern in ['output/', '.jpg', '.HEIC', '.DS_Store'])]
    
    if important_changes:
        print("❌ Error: You have uncommitted changes to source files:")
        for change in important_changes:
            print(f"   {change}")
        print("\nPlease commit your changes before deploying:")
        print("   git add .")
        print("   git commit -m 'Your commit message'")
        sys.exit(1)
    
    # Step 3: Create/switch to gh-pages branch
    print("\n🌿 Step 3: Setting up gh-pages branch...")
    
    # Check if gh-pages branch exists
    branch_exists = False
    try:
        subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/gh-pages"], 
                      check=True, capture_output=True)
        branch_exists = True
    except subprocess.CalledProcessError:
        pass
    
    if branch_exists:
        print("gh-pages branch exists, switching to it...")
        run_command("git checkout gh-pages")
    else:
        print("Creating new gh-pages branch...")
        run_command("git checkout --orphan gh-pages")
        
        # Remove all files from the new orphan branch
        subprocess.run(["git", "rm", "-rf", "."], capture_output=True)
    
    # Step 4: Copy site files to branch
    print("\n📁 Step 4: Copying generated site files...")
    
    # Save current working directory
    original_dir = Path.cwd()
    
    # First, save the generated site and web_photos to temp locations
    run_command(f"mkdir -p /tmp/treepics")
    temp_site = Path("/tmp/treepics/temp_treepics_site")
    temp_photos = Path("/tmp/treepics/temp_treepics_photos")
    
    if temp_site.exists():
        shutil.rmtree(temp_site)
    if temp_photos.exists():
        shutil.rmtree(temp_photos)
    
    # Go back to source branch to get the built site and web_photos
    run_command(f"git checkout {current_branch}")
    if not site_dir.exists():
        print("❌ Site not found. Running build first...")
        run_command("uv run python main.py")
    
    # Copy the built site and web_photos to temp locations
    shutil.copytree(site_dir, temp_site)
    web_photos_dir = Path("web_photos")
    if web_photos_dir.exists():
        shutil.copytree(web_photos_dir, temp_photos)
    
    # Switch back to gh-pages and clear it
    run_command("git checkout gh-pages")
    
    # Clear any existing files (except .git)
    for item in Path('.').iterdir():
        if item.name != '.git':
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    
    # Copy all files from temp site to root of gh-pages (not in treepics-map subdir)
    for item in temp_site.iterdir():
        if item.is_dir():
            shutil.copytree(item, item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, '.')

    ### Seth TODO: this ^ doesn't seem to be working. Hack incoming...


    ### Seth: I'm not sure this is necessary, but if so it would need to be before the hack
    # Replace the photos directory with web_photos content
    if Path(web_photos_dir).exists():
        shutil.rmtree(web_photos_dir)
    if temp_photos.exists():
        shutil.copytree(temp_photos, web_photos_dir)
    

    #### end hack

    
    # Clean up temp directories
    if temp_site.exists():
        shutil.rmtree(temp_site)
    if temp_photos.exists():
        shutil.rmtree(temp_photos)
    
    print("✅ Site files and photos copied to gh-pages branch!")
    
    # Step 5: Commit and push
    print("\n📤 Step 5: Committing and pushing to GitHub...")
    
    run_command("git add .")
    
    # Check if there are changes to commit
    try:
        run_command("git diff --staged --quiet")
        print("ℹ️  No changes to commit. Site is up to date.")
    except subprocess.CalledProcessError:
        # There are changes to commit
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_command(f'git commit -m "Deploy TreePics Map - {timestamp}"')
        print("✅ Changes committed!")
        
        print("Pushing to GitHub...")
        run_command("git push origin gh-pages")
        print("🚀 Successfully deployed to GitHub Pages!")
    
    # Step 6: Switch back to original branch
    print(f"\n🔄 Step 6: Switching back to {current_branch} branch...")
    run_command(f"git checkout {current_branch}")
    
    print("\n🎉 Deployment Complete!")
    print("=" * 50)
    print("Your TreePics Map should be available at:")
    
    # Try to get the GitHub repo URL
    try:
        remote_url = run_command("git remote get-url origin")
        if "github.com" in remote_url:
            # Extract username/repo from URL
            if remote_url.startswith("git@github.com:"):
                repo_part = remote_url.replace("git@github.com:", "").replace(".git", "")
            elif remote_url.startswith("https://github.com/"):
                repo_part = remote_url.replace("https://github.com/", "").replace(".git", "")
            else:
                repo_part = "username/repository"
            
            print(f"🌐 https://{repo_part.replace('/', '.github.io/')}")
        else:
            print("🌐 Configure GitHub Pages in your repository settings")
    except:
        print("🌐 Configure GitHub Pages in your repository settings")
    
    print("\nNext steps:")
    print("1. Go to your GitHub repository settings")
    print("2. Navigate to 'Pages' in the left sidebar")
    print("3. Set source to 'Deploy from a branch'")
    print("4. Select 'gh-pages' branch and '/ (root)' folder")
    print("5. Click 'Save'")

if __name__ == "__main__":
    main()