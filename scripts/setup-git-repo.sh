#!/bin/bash

# Script to initialize git repository and push to remote
# Usage: ./scripts/setup-git-repo.sh <repository-url>

set -e

REPO_URL="$1"

if [ -z "$REPO_URL" ]; then
    echo "❌ Error: Repository URL is required"
    echo ""
    echo "Usage: ./scripts/setup-git-repo.sh <repository-url>"
    echo ""
echo "Examples:"
echo "  ./scripts/setup-git-repo.sh https://github.com/cellango/SentinelGrid.git"
echo "  ./scripts/setup-git-repo.sh git@github.com:cellango/SentinelGrid.git"
echo ""
echo "Note: Repository name should be 'SentinelGrid' to match the project folder name"
    exit 1
fi

echo "🚀 Setting up git repository..."
echo ""

# Check if already a git repository
if [ -d ".git" ]; then
    echo "⚠️  Warning: This directory is already a git repository"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    # Initialize git repository
    echo "📦 Initializing git repository..."
    git init
fi

# Check if remote already exists
if git remote get-url origin >/dev/null 2>&1; then
    echo "⚠️  Warning: Remote 'origin' already exists"
    CURRENT_URL=$(git remote get-url origin)
    echo "   Current URL: $CURRENT_URL"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote set-url origin "$REPO_URL"
        echo "✅ Updated remote URL to: $REPO_URL"
    else
        echo "ℹ️  Keeping existing remote URL"
    fi
else
    # Add remote
    echo "🔗 Adding remote repository..."
    git remote add origin "$REPO_URL"
    echo "✅ Added remote: $REPO_URL"
fi

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo ""
    echo "📝 Staging all files..."
    git add .
    
    echo ""
    echo "💾 Creating initial commit..."
    git commit -m "Initial commit: SentinelGrid security platform"
    echo "✅ Created initial commit"
else
    echo "ℹ️  No changes to commit"
fi

# Set main branch
echo ""
echo "🌿 Setting main branch..."
git branch -M main 2>/dev/null || echo "ℹ️  Already on main branch"

# Push to remote
echo ""
echo "📤 Pushing to remote repository..."
echo "   This may prompt for credentials..."
echo ""

if git push -u origin main; then
    echo ""
    echo "✅ Successfully pushed to remote repository!"
    echo ""
    echo "🎉 Your repository is now set up at: $REPO_URL"
else
    echo ""
    echo "❌ Failed to push to remote repository"
    echo ""
    echo "Common issues:"
    echo "  1. Authentication required - make sure you have SSH keys set up or use HTTPS with credentials"
    echo "  2. Repository doesn't exist - verify the URL is correct"
    echo "  3. Network issues - check your internet connection"
    echo ""
    echo "You can manually push later with:"
    echo "  git push -u origin main"
    exit 1
fi

