# Contributing to Vantage Q-Link Bridge

Thank you for your interest in contributing! This project aims to make Vantage lighting systems accessible to modern home automation platforms.

## 🎯 Ways to Contribute

- **Report Bugs** - Found an issue? Open a bug report with details
- **Feature Requests** - Have an idea? Share it in the discussions
- **Documentation** - Help improve guides, examples, and API docs
- **Code** - Submit bug fixes, features, or improvements
- **Testing** - Test on different Vantage systems and report compatibility

## 🚀 Getting Started

### Development Setup

1. **Fork and Clone**
```bash
git clone https://github.com/yourusername/vantage-qlink-bridge.git
cd vantage-qlink-bridge
```

2. **Create Virtual Environment**
```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r app/requirements.txt
pip install -r dev-requirements.txt  # When available
```

4. **Run Locally**
```bash
# Set test environment variables
export VANTAGE_IP="192.168.1.200"
export VANTAGE_PORT="3041"

# Start the bridge
python -m uvicorn app.bridge:app --reload --host 0.0.0.0 --port 8000
```

5. **Test Your Changes**
```bash
# Run tests (when available)
pytest tests/

# Test manually
curl http://localhost:8000/healthz
curl http://localhost:8000/config
```

## 📝 Contribution Guidelines

### Creating a Pull Request

1. **Create a Feature Branch**
```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/issue-123
```

2. **Make Your Changes**
- Write clear, descriptive commit messages
- Keep commits focused and atomic
- Follow existing code style

3. **Test Thoroughly**
- Test with actual Vantage hardware if possible
- Verify no regressions in existing features
- Check edge cases

4. **Submit PR**
- Push your branch to your fork
- Open a Pull Request against `main`
- Describe what changed and why
- Reference any related issues

### Commit Message Format

Use clear, descriptive commit messages:

```
feat: Add WebSocket event streaming support
fix: Correct VSW@ command format per Q-Link docs
docs: Update README with event monitoring examples
refactor: Extract event parsing into separate function
test: Add unit tests for button press commands
```

### Code Style

- **Python**: Follow PEP 8
- **Formatting**: Use `black` (when configured)
- **Linting**: Use `ruff` or `pylint` (when configured)
- **Type Hints**: Add type hints where beneficial
- **Comments**: Explain "why", not "what"

Example:
```python
def parse_vantage_event(message: str) -> Optional[dict]:
    """Parse SW/LO/LE events from Vantage controller.

    Args:
        message: Raw event string from Q-Link protocol

    Returns:
        Parsed event dict or None if not recognized
    """
    # SW events have variable fields depending on serial presence
    if message.startswith("SW "):
        parts = message.split()
        # ... parsing logic
```

### Testing

- Add tests for new features in `tests/`
- Run existing tests before submitting PR
- Include integration tests if applicable

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_app.py

# Run with coverage
pytest --cov=app tests/
```

## 🐛 Reporting Bugs

When reporting bugs, include:

1. **Description** - What happened vs what you expected
2. **Environment**
   - OS (Raspberry Pi OS, Ubuntu, etc.)
   - Python version
   - Bridge version
3. **Vantage System**
   - Controller model
   - Firmware version
   - Q-Link port configuration
4. **Steps to Reproduce**
5. **Logs** - Include relevant error messages
6. **Screenshots** - If applicable

### Bug Report Template

```markdown
**Description**
Brief description of the issue

**Environment**
- OS: Raspberry Pi OS Bullseye
- Python: 3.11.2
- Bridge: 0.4.0

**Vantage System**
- Controller: InFusion Controller
- Firmware: X.XX
- Port: 3041

**Steps to Reproduce**
1. Start bridge
2. Send command X
3. Observe error Y

**Expected Behavior**
What should have happened

**Actual Behavior**
What actually happened

**Logs**
```
[paste relevant logs]
```

**Additional Context**
Any other relevant information
```

## 💡 Feature Requests

We welcome feature requests! Before submitting:

1. **Check Existing Issues** - See if already requested
2. **Describe Use Case** - Explain why it's needed
3. **Propose Solution** - If you have ideas on implementation

## 🔒 Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email the maintainer directly (see README)
3. Provide detailed description
4. We'll respond within 48 hours

## 📚 Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples for common scenarios
- Expand API documentation
- Create tutorials or guides
- Add diagrams or screenshots

## 🎨 UI/UX Contributions

For web interface improvements:

- Keep design simple and accessible
- Test on mobile devices
- Ensure keyboard navigation works
- Follow existing color scheme
- Test on different screen sizes

## 🤝 Code Review Process

1. Maintainer reviews PR within 1 week
2. Feedback provided via PR comments
3. Address requested changes
4. Once approved, PR is merged
5. Your contribution is acknowledged in CHANGELOG

## 📋 Development Roadmap

See [TASKS.md](TASKS.md) for current priorities:

- SmartThings Edge driver integration
- Complete button extraction automation
- Enhanced error handling
- Configuration persistence
- Unit test coverage

## 📞 Questions?

- Open a [Discussion](https://github.com/yourusername/vantage-qlink-bridge/discussions)
- Check existing [Issues](https://github.com/yourusername/vantage-qlink-bridge/issues)
- Review [Documentation](docs/)

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to the Vantage Q-Link Bridge! 🎉
