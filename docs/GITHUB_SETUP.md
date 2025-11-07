# GitHub Repository Creation Guide

> **🔴 Having issues with CI checks (Red X)?** See [Understanding GitHub Features](GITHUB_FEATURES.md) for troubleshooting help!

> **🟢 Wondering what "Compare & pull request" does?** See [Understanding GitHub Features](GITHUB_FEATURES.md) for a complete guide!

## 🚀 Step-by-Step GitHub Setup

### Prerequisites (You Have These!)
✅ VS Code installed
✅ GitHub extension installed
✅ Git installed
✅ Project ready to publish

### Step 1: Initialize Git Repository

Open PowerShell in your project folder and run:

```powershell
cd C:\Qlink

# Initialize git repository
git init

# Configure your identity (replace with your info)
git config user.name "Your GitHub Username"
git config user.email "your.github@email.com"

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - Vantage Q-Link Bridge v0.4.0"
```

### Step 2: Create GitHub Repository (Using VS Code)

**Method A: Using VS Code GitHub Extension (Easiest!)**

1. **Open Command Palette**: Press `Ctrl+Shift+P`
2. **Type**: "GitHub: Publish to GitHub"
3. **Select**: "Publish to GitHub" from the list
4. **Choose**:
   - Repository name: `vantage-qlink-bridge`
   - Description: "Modern REST API bridge for Vantage lighting control systems"
   - Visibility: **Public** (to share with community)
5. **Click**: "Publish" button
6. **Done!** VS Code will create the repo and push your code

**Method B: Using GitHub Website (Alternative)**

1. **Go to**: https://github.com/new
2. **Repository name**: `vantage-qlink-bridge`
3. **Description**: "Modern REST API bridge for Vantage lighting control systems"
4. **Visibility**: Public ✅
5. **Initialize**:
   - ❌ Don't add README (we have one)
   - ❌ Don't add .gitignore (we have one)
   - ❌ Don't add license (we have MIT)
6. **Click**: "Create repository"

### Step 3: Push Your Code (If using Method B)

After creating the repo on GitHub:

```powershell
# Add GitHub as remote
git remote add origin https://github.com/YOUR-USERNAME/vantage-qlink-bridge.git

# Push your code
git branch -M main
git push -u origin main
```

### Step 4: Configure Repository Settings

On GitHub website, go to your repository settings:

1. **About Section** (right side):
   - Click ⚙️ (gear icon)
   - Add description: "Modern REST API bridge for Vantage lighting control systems"
   - Add topics: `vantage`, `home-automation`, `lighting-control`, `smart-home`, `raspberry-pi`, `qlink`, `rest-api`
   - ✅ Check "Releases"
   - ✅ Check "Packages"
   - Save

2. **Features** (Settings → General):
   - ✅ Issues
   - ✅ Discussions (optional)
   - ✅ Wiki (optional)
   - ❌ Projects (not needed yet)

### Step 5: Create First Release

1. Go to: **Releases** → **Create a new release**
2. **Tag**: `v0.4.0`
3. **Release title**: `v0.4.0 - Initial Release`
4. **Description**: Copy from CHANGELOG.md:

```markdown
## Features
- Real-time event monitoring via WebSocket
- Modern web interface with dark theme
- Settings management without SSH
- Automatic button extraction (470 buttons!)
- Complete configuration manager
- Mobile-responsive design

## What's Included
- REST API for Vantage control
- Web UI (Control, Settings, Configuration)
- 470 buttons pre-configured across 71 stations
- Complete documentation
- Deployment scripts for Raspberry Pi

See CHANGELOG.md for full details.
```

5. Click **"Publish release"**

### Step 6: Update URLs in Documentation

After creating the repository, update these placeholders:

**In README.md**, replace:
- `yourusername` → your actual GitHub username
- Repository URLs

**In CONTRIBUTING.md**, update:
- Issue tracker URL
- Discussions URL

### Step 7: Add Repository Badges (Optional but Cool!)

Add to top of README.md:

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub release](https://img.shields.io/github/release/YOUR-USERNAME/vantage-qlink-bridge.svg)](https://github.com/YOUR-USERNAME/vantage-qlink-bridge/releases)
[![GitHub stars](https://img.shields.io/github/stars/YOUR-USERNAME/vantage-qlink-bridge.svg)](https://github.com/YOUR-USERNAME/vantage-qlink-bridge/stargazers)
```

## 🎯 Quick Commands Reference

```powershell
# Check status
git status

# Add new files
git add .

# Commit changes
git commit -m "Your message here"

# Push to GitHub
git push

# Create new branch
git checkout -b feature-name

# View remotes
git remote -v

# Pull latest changes
git pull
```

## 🔐 Authentication Options

### Option 1: HTTPS with Personal Access Token (Recommended)
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `workflow`
4. Copy token
5. Use as password when pushing

### Option 2: SSH Key
1. Generate SSH key: `ssh-keygen -t ed25519 -C "your.email@example.com"`
2. Add to GitHub: Settings → SSH and GPG keys
3. Change remote to SSH:
   ```powershell
   git remote set-url origin git@github.com:USERNAME/vantage-qlink-bridge.git
   ```

### Option 3: GitHub Desktop (Easiest)
1. Download GitHub Desktop
2. File → Add local repository → Browse to C:\Qlink
3. Publish repository button
4. Done!

## 📋 Pre-Publication Checklist

Before making repository public:

- [x] README.md complete with documentation
- [x] LICENSE file (MIT) present
- [x] .gitignore configured
- [x] CONTRIBUTING.md with guidelines
- [x] CHANGELOG.md up to date
- [x] CODE_OF_CONDUCT.md present
- [x] No sensitive data (passwords, IPs, keys)
- [x] Example configurations provided
- [ ] Update username placeholders
- [ ] Test links after publication
- [ ] Add topics/tags
- [ ] Create initial release

## 🎉 After Publishing

1. **Share it!**
   - Post on Reddit (r/homeautomation, r/smarthome)
   - Tweet about it
   - Add to awesome-home-automation lists

2. **Monitor**
   - Watch for issues
   - Respond to discussions
   - Accept pull requests

3. **Maintain**
   - Update CHANGELOG for new versions
   - Create releases for major updates
   - Keep documentation current

## 🆘 Troubleshooting

### Red X on Initial Commit (CI Failed)
→ See detailed guide: [Understanding GitHub Features](GITHUB_FEATURES.md)
→ Click on the red X to see error details
→ Common fix: Update package versions in `dev-requirements.txt`
→ Run tests locally: `pytest` and `ruff .` before pushing

### Green "Compare & pull request" Button
→ See detailed guide: [Understanding GitHub Features](GITHUB_FEATURES.md)
→ Click this when ready to merge your changes
→ Creates a Pull Request for code review
→ Waits for CI checks to pass before merging

### "Permission denied" when pushing
→ Set up authentication (see above)

### "Repository not found"
→ Check remote URL: `git remote -v`
→ Update: `git remote set-url origin https://github.com/USERNAME/REPO.git`

### "Failed to push some refs"
→ Pull first: `git pull origin main`
→ Resolve conflicts if any
→ Then push: `git push`

### Large file warning
→ Files should be < 100MB
→ Use Git LFS for large files if needed

## 📞 Need Help?

VS Code has great Git integration:
- View Source Control panel (Ctrl+Shift+G)
- Click "..." menu for all git operations
- View Git Graph for visual history

---

**Your repository will be at:**
`https://github.com/YOUR-USERNAME/vantage-qlink-bridge`

**Ready to share your awesome project with the world!** 🚀
