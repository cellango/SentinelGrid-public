# Instructions for Creating a Private Repository

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Option 1: GitHub (Recommended)

1. Go to https://github.com/new
2. Repository name: `SentinelGrid` (matches project folder name)
3. Description: "SentinelGrid Security Platform"
4. **Select "Private"**
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

After creation, GitHub will show you commands. Use the commands below instead (they're tailored for this project).

## Option 2: GitLab

1. Go to https://gitlab.com/projects/new
2. Click "Create blank project"
3. Project name: `SentinelGrid` (matches project folder name)
4. **Select "Private"**
5. **DO NOT** initialize with README
6. Click "Create project"

## Option 3: Bitbucket

1. Go to https://bitbucket.org/repo/create
2. Repository name: `SentinelGrid` (matches project folder name)
3. **Select "Private"**
4. Click "Create repository"

## After Creating the Repository

Once you have created the repository, run:

```bash
# Initialize git repository
git init

# Add all files (respecting .gitignore)
git add .

# Create initial commit
git commit -m "Initial commit: SentinelGrid security platform"

# Add remote
git remote add origin https://github.com/cellango/SentinelGrid.git

# Push to remote
git branch -M main
git push -u origin main
```

## Repository URL Format

The repository name should be **`SentinelGrid`** to match your project folder name.

- **HTTPS**: `https://github.com/cellango/SentinelGrid.git`
- **SSH**: `git@github.com:cellango/SentinelGrid.git`

Use SSH if you have SSH keys set up, otherwise use HTTPS.

