# Understanding GitHub Features

This guide explains common GitHub features you'll encounter when working with your repository.

## 🔴 Red X - Failed CI Check (What You're Seeing)

### What is the Red X?

When you see a **red X** next to your commit or on your pull request, it means that **GitHub Actions (CI/CD) checks have failed**.

### Why Does This Happen?

GitHub Actions runs automated tests and checks on your code when you:
- Push commits to a branch
- Create or update a pull request
- Merge code

The red X appears when:
- ✗ Tests fail
- ✗ Code doesn't meet linting standards
- ✗ Dependencies can't be installed
- ✗ Build process fails

### How to Fix the Red X

#### Step 1: Click on the Red X

Click the red X next to your commit to see which check failed.

#### Step 2: View the Failed Workflow

You'll see something like:
```
CI / test (pull_request) — Failed
```

Click "Details" to see the full log.

#### Step 3: Read the Error Message

Look for error messages in the log. Common issues:

**Example 1: Dependency Installation Failed**
```
ERROR: No matching distribution found for pre-commit==4.5.0
```
**Solution**: Update the version in `dev-requirements.txt`

**Example 2: Tests Failed**
```
FAILED tests/test_app.py::test_healthz - AssertionError
```
**Solution**: Fix the failing test or the code it's testing

**Example 3: Linting Failed**
```
ruff found 5 errors
```
**Solution**: Run linters locally and fix issues

#### Step 4: Fix Locally and Push

```bash
# Fix the issue in your code
# Test locally first
pytest
black .
ruff .

# Commit and push the fix
git add .
git commit -m "Fix CI issues"
git push
```

### Checking CI Status

On your repository page:
- ✅ **Green checkmark** = All checks passed
- 🔴 **Red X** = Some checks failed
- 🟡 **Yellow circle** = Checks are running
- ⚪ **Gray dot** = No checks configured or pending

## 🟢 Green "Compare & pull request" Button

### What Does This Button Do?

When you push a branch to GitHub, you'll see a banner with a green **"Compare & pull request"** button:

```
[i] Your recently pushed branches:
    copilot/fix-initial-commit-issue (2 minutes ago)
    
    [Compare & pull request]  <-- This green button
```

### What Happens When You Click It?

This button:
1. **Opens a Pull Request (PR) creation page**
2. **Pre-fills** the PR with:
   - Your branch name
   - Recent commits
   - Suggested title from your commit messages
3. **Allows you to**:
   - Add a description
   - Assign reviewers
   - Add labels
   - Set milestones

### Should You Click It?

**YES** - Click it when you want to:
- Merge your changes into the main branch
- Get code review from others
- Run CI checks on your changes
- Start a discussion about your changes

**NO** - Don't click it if:
- You're still working on the feature
- You want to add more commits first
- The branch is not ready for review

### Alternative: Manual Pull Request

You can also create a PR manually:
1. Go to "Pull requests" tab
2. Click "New pull request"
3. Select your branch
4. Click "Create pull request"

## 🔵 "Sync fork" Button (For Forked Repositories)

If you forked this repository, you might see a **"Sync fork"** button:

```
[Sync fork] ▼
```

### What Does It Do?

- Updates your fork with changes from the original repository
- Keeps your fork up-to-date

### How to Use It

1. Click "Sync fork"
2. Review the incoming changes
3. Click "Update branch" to sync

## 📊 Understanding GitHub Actions Workflow

### Your Repository's CI Workflow

Location: `.github/workflows/ci.yml`

What it does:
```yaml
1. Checks out your code
2. Sets up Python 3.11
3. Installs dependencies from dev-requirements.txt
4. Runs linters (ruff and black)
5. Runs tests (pytest)
```

### Running CI Checks Locally (Before Pushing)

To avoid the red X, run these commands locally:

```bash
# Install dependencies
pip install -r dev-requirements.txt

# Run linters
ruff .
black --check .

# Run tests
pytest -q

# If everything passes, you're good to push!
```

### Setting Up Pre-commit Hooks

Pre-commit hooks run checks automatically before each commit:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install

# Now checks run automatically on git commit
git commit -m "Your message"  # Linters run first!
```

## 🎯 Common Scenarios

### Scenario 1: Red X on Initial Commit

**Problem**: First commit has red X

**Common Causes**:
- Invalid package versions in requirements
- Missing dependencies
- Failing tests in starting code

**Solution**:
```bash
# Fix the issue
# In this case, update dev-requirements.txt

# Commit the fix
git add dev-requirements.txt
git commit -m "Fix: Update pre-commit version to 4.3.0"
git push
```

### Scenario 2: Want to Merge Changes

**Steps**:
1. Ensure CI passes (green checkmark ✅)
2. Click "Compare & pull request"
3. Fill in PR description
4. Request reviews if needed
5. Click "Create pull request"
6. Wait for approval
7. Click "Merge pull request"

### Scenario 3: PR Has Red X

**Steps**:
1. Click Details on the red X
2. Identify the failing check
3. Fix the issue locally
4. Push new commits
5. CI automatically re-runs
6. Green checkmark means ready to merge

## 📝 Best Practices

### Before Creating a Pull Request

- [ ] All tests pass locally (`pytest`)
- [ ] Code is properly formatted (`black .`)
- [ ] No linting errors (`ruff .`)
- [ ] Commit messages are clear
- [ ] Changes are tested

### When You See a Red X

1. **Don't panic** - It's just automated feedback
2. **Read the logs** - They tell you exactly what's wrong
3. **Fix locally first** - Test before pushing
4. **Ask for help** - Open an issue if stuck

### Keeping CI Green

```bash
# Create a script to run before pushing
# Save as scripts/pre-push.sh

#!/bin/bash
echo "Running checks..."
ruff . && black --check . && pytest -q
if [ $? -eq 0 ]; then
    echo "✅ All checks passed! Safe to push."
else
    echo "❌ Checks failed. Fix issues before pushing."
    exit 1
fi
```

## 🔧 Troubleshooting

### CI Always Fails with Same Error

**Check**:
- Is the error in your code or in CI configuration?
- Are dependency versions correct?
- Does it work locally?

**Fix**:
- Update `.github/workflows/ci.yml` if needed
- Update `dev-requirements.txt` with correct versions
- Ensure local environment matches CI

### Can't Find CI Logs

**Steps**:
1. Go to "Actions" tab in your repository
2. Click on the failing workflow run
3. Click on the failed job
4. Read the log output

### Want to Skip CI

You can skip CI for specific commits (use sparingly):

```bash
git commit -m "Update README [skip ci]"
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [About Pull Requests](https://docs.github.com/en/pull-requests)
- [About Status Checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)

## 🆘 Quick Reference

| Symbol | Meaning | Action |
|--------|---------|--------|
| 🔴 Red X | CI Failed | Click Details, fix issue, push |
| ✅ Green Check | CI Passed | Safe to merge |
| 🟡 Yellow Circle | CI Running | Wait for completion |
| 🟢 Compare & PR | Create PR | Click when ready to merge |
| 🔵 Sync Fork | Update Fork | Click to get latest changes |

---

**Remember**: The red X is your friend! It catches issues before they reach production. Fix it, learn from it, and move forward. 🚀
