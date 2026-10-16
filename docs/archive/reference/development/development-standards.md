# SentinelGrid Development Standards

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Establish consistent development practices for all developers and AI agents

**Last Updated:** December 5, 2025

---

## 📚 Documentation Standards

### Location: All Documentation in `docs/` Folder

**Rule:** All documentation files (`.md`, `.txt`, etc.) **MUST** be placed in the `docs/` folder.

**Exceptions:**
- `README.md` in project root (standard practice)
- `README.md` files in subdirectories (component-specific)
- Configuration files with documentation (e.g., `docker-compose.yml` comments)

**Structure:**
```
docs/
├── PLATFORM_ADMIN_GUIDE.md          # Platform admin documentation
├── DEVELOPMENT_STANDARDS.md          # This file
├── PRODUCTION_SECURITY_CHECKLIST.md # Security documentation
├── REALM_ARCHITECTURE_IMPLEMENTATION.md
├── IAM_IMPLEMENTATION_STATUS.md
└── ... (all other documentation)
```

**Why:**
- ✅ Centralized location for all documentation
- ✅ Easy to find and maintain
- ✅ Clean project root
- ✅ Better organization for AI agents
- ✅ Consistent structure for new developers

**What to Move:**
- All `.md` files from project root → `docs/`
- All documentation `.txt` files → `docs/`
- Implementation summaries → `docs/`
- Status reports → `docs/`
- Architecture documents → `docs/`

**What to Keep in Root:**
- `README.md` (project overview)
- Configuration files (`.yml`, `.yaml`, `.json`, etc.)
- Scripts (`.sh`, `.py`, etc.)

---

## 🧪 Testing Standards

### 1. Conda Test Environment

**Rule:** All tests **MUST** run in a dedicated Conda test environment.

**Setup:**
```bash
# Create test environment
conda create -n sentinelgrid-test python=3.11
conda activate sentinelgrid-test

# Install test dependencies
pip install -r requirements-test.txt
pip install pytest pytest-cov pytest-asyncio
```

**Usage:**
```bash
# Activate test environment
conda activate sentinelgrid-test

# Run tests
pytest backend/tests/

# Run with coverage
pytest --cov=backend backend/tests/
```

**Why:**
- ✅ Isolated test dependencies
- ✅ Reproducible test environment
- ✅ No conflicts with development dependencies
- ✅ Consistent across all developers

### 2. Docker Testing with Volume Mounts

**Rule:** All testing **MUST** be done in Docker with volumes pointing to development code.

**Configuration:**
```yaml
# docker-compose.test.yml
services:
  test_runner:
    image: python:3.11
    volumes:
      - ./backend:/app/backend:ro          # Read-only mount
      - ./backend/tests:/app/tests:rw      # Read-write for test results
      - ./backend/requirements.txt:/app/requirements.txt:ro
    working_dir: /app
    command: pytest tests/
```

**Benefits:**
- ✅ **Efficiency:** Code changes reflected immediately (no rebuild)
- ✅ **Isolation:** Tests run in clean container environment
- ✅ **Consistency:** Same environment for all developers
- ✅ **Speed:** No need to rebuild images for code changes

**Volume Mount Strategy:**
```yaml
volumes:
  # Development code (read-only)
  - ./backend:/app/backend:ro
  
  # Test code (read-write for results)
  - ./backend/tests:/app/tests:rw
  
  # Test results/output
  - ./test-results:/app/test-results:rw
  
  # Dependencies (read-only)
  - ./requirements.txt:/app/requirements.txt:ro
```

**Example Test Setup:**
```bash
# Run tests in Docker with volume mounts
docker-compose -f docker-compose.test.yml run --rm test_runner

# Or use Makefile
make test
```

**Why Volume Mounts:**
- ✅ **No Rebuilds:** Code changes instantly available
- ✅ **Fast Iteration:** Edit code, run tests immediately
- ✅ **Development Efficiency:** See results without waiting for builds
- ✅ **AI Agent Friendly:** Quick feedback loops

---

## 📁 Project Structure Standards

### Root Directory

**Keep Clean:**
```
SentinelGrid/
├── README.md                    # ✅ Project overview (keep in root)
├── docker-compose.dev.yml       # ✅ Configuration files
├── docker-compose.test.yml      # ✅ Test configuration
├── Makefile                     # ✅ Build automation
├── .gitignore                   # ✅ Git configuration
├── docs/                        # ✅ ALL documentation here
├── backend/                     # ✅ Backend code
├── frontend/                    # ✅ Frontend code
├── infra/                       # ✅ Infrastructure code
└── scripts/                     # ✅ Utility scripts
```

**Do NOT Put in Root:**
- ❌ Documentation files (`.md` except `README.md`)
- ❌ Implementation summaries
- ❌ Status reports
- ❌ Architecture documents
- ❌ Test results
- ❌ Temporary files

### Documentation Structure

```
docs/
├── DEVELOPMENT_STANDARDS.md          # Development standards (this file)
├── PLATFORM_ADMIN_GUIDE.md            # Platform admin guide
├── PRODUCTION_SECURITY_CHECKLIST.md   # Security checklist
├── REALM_ARCHITECTURE_IMPLEMENTATION.md
├── IAM_IMPLEMENTATION_STATUS.md
├── DOCKER_AUDIT_REPORT.md
├── README.md                          # Documentation index
└── ... (all other documentation)
```

---

## 🔧 Development Workflow

### 1. Code Development

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# Edit code in backend/, frontend/, etc.

# 3. Test locally (Conda environment)
conda activate sentinelgrid-test
pytest backend/tests/

# 4. Test in Docker (with volume mounts)
docker-compose -f docker-compose.test.yml run --rm test_runner

# 5. Commit and push
git commit -m "Add feature X"
git push origin feature/my-feature
```

### 2. Documentation

```bash
# 1. Create documentation in docs/ folder
# docs/MY_FEATURE.md

# 2. Update docs/README.md if needed
# Add entry to documentation index

# 3. Commit documentation
git add docs/MY_FEATURE.md
git commit -m "Add documentation for feature X"
```

### 3. Testing

```bash
# Option 1: Conda environment (local)
conda activate sentinelgrid-test
pytest backend/tests/

# Option 2: Docker with volume mounts (recommended)
docker-compose -f docker-compose.test.yml run --rm test_runner

# Option 3: Full Docker stack
docker-compose -f docker-compose.test.yml up test_runner
```

---

## 🤖 AI Agent Guidelines

### For AI Agents Working on This Codebase

**Documentation:**
- ✅ Always create documentation in `docs/` folder
- ✅ Never create `.md` files in project root
- ✅ Update `docs/README.md` index when adding new docs
- ✅ Follow existing documentation structure

**Testing:**
- ✅ Always use Conda test environment for local tests
- ✅ Always use Docker with volume mounts for integration tests
- ✅ Never hardcode paths - use relative paths from project root
- ✅ Ensure tests can run without rebuilding images

**Code Organization:**
- ✅ Follow existing project structure
- ✅ Keep root directory clean
- ✅ Place scripts in appropriate `scripts/` directories
- ✅ Place configuration in appropriate locations

**Examples:**

**❌ Wrong:**
```bash
# Creating doc in root
echo "# Feature" > FEATURE.md

# Testing without environment
pytest tests/

# Hardcoded paths
import sys
sys.path.append('/Users/developer/SentinelGrid')
```

**✅ Correct:**
```bash
# Creating doc in docs/
echo "# Feature" > docs/FEATURE.md

# Testing with Conda
conda activate sentinelgrid-test
pytest backend/tests/

# Relative paths
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
```

---

## 📋 Checklist for New Developers

### Setup

- [ ] Clone repository
- [ ] Read `README.md` in root
- [ ] Read `docs/archive/reference/development/development-standards.md` (this file)
- [ ] Set up Conda test environment
- [ ] Configure Docker for testing
- [ ] Review `docs/README.md` for documentation index

### Development

- [ ] Create feature branch
- [ ] Write code following project structure
- [ ] Write tests in appropriate test directories
- [ ] Run tests in Conda environment
- [ ] Run tests in Docker with volume mounts
- [ ] Create documentation in `docs/` folder
- [ ] Update documentation index if needed

### Before Committing

- [ ] All tests pass in Conda environment
- [ ] All tests pass in Docker
- [ ] Documentation is in `docs/` folder
- [ ] No temporary files in root
- [ ] Code follows project structure
- [ ] No hardcoded paths

---

## 🚀 Quick Reference

### Documentation

```bash
# Create new documentation
touch docs/MY_FEATURE.md

# View documentation index
cat docs/README.md

# Find documentation
find docs/ -name "*.md" | grep -i "keyword"
```

### Testing

```bash
# Setup Conda environment
conda create -n sentinelgrid-test python=3.11
conda activate sentinelgrid-test
pip install -r requirements-test.txt

# Run tests (Conda)
conda activate sentinelgrid-test
pytest backend/tests/

# Run tests (Docker with volumes)
docker-compose -f docker-compose.test.yml run --rm test_runner
```

### Docker Testing

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run tests with volume mounts
docker-compose -f docker-compose.test.yml run --rm test_runner pytest

# View test results
docker-compose -f docker-compose.test.yml exec test_runner cat test-results/results.xml
```

---

## 📝 File Naming Conventions

### Documentation Files

**Format:** `UPPERCASE_WITH_UNDERSCORES.md`

**Examples:**
- `PLATFORM_ADMIN_GUIDE.md`
- `DEVELOPMENT_STANDARDS.md`
- `PRODUCTION_SECURITY_CHECKLIST.md`
- `REALM_ARCHITECTURE_IMPLEMENTATION.md`

**Why:**
- ✅ Easy to spot in file listings
- ✅ Consistent naming
- ✅ Clear purpose from filename

### Test Files

**Format:** `test_*.py` or `*_test.py`

**Examples:**
- `test_auth.py`
- `test_realm_manager.py`
- `auth_test.py`

---

## 🔍 Finding Things

### Where to Look

**Documentation:**
- Start: `docs/README.md` (index)
- Search: `find docs/ -name "*.md" | grep keyword`

**Tests:**
- Backend: `backend/tests/`
- Services: `backend/services/*/tests/`
- Agents: `backend/agents/*/tests/`

**Configuration:**
- Docker: `docker-compose.*.yml`
- Infrastructure: `infra/`
- Scripts: `backend/scripts/`, `scripts/`

---

## ❓ Questions?

**Documentation Questions:**
- See `docs/README.md` for documentation index
- See `docs/archive/reference/platform/platform-admin-guide.md` for platform admin docs

**Testing Questions:**
- See `backend/tests/README.md` for test documentation
- See `docker-compose.test.yml` for test configuration

**Development Questions:**
- See this file (`DEVELOPMENT_STANDARDS.md`)
- See `README.md` in project root

---

## 📚 Related Documentation

- `docs/README.md` - Documentation index
- `README.md` - Project overview
- `backend/tests/README.md` - Test documentation
- `docker-compose.test.yml` - Test configuration

---

**Last Updated:** December 5, 2025  
**Maintained By:** Platform Engineering Team  
**Version:** 1.0

