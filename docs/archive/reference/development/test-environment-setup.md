# Test Environment Setup Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Conda Environment

SentinelGrid tests use a dedicated conda environment called `SentinelTest` to ensure consistent dependencies across different systems.

## Quick Setup

### 1. Create Conda Environment

```bash
cd backend/tests
./setup-conda-env.sh
```

Or manually:

```bash
conda env create -f backend/tests/environment.yml
conda activate SentinelTest
```

### 2. Activate Environment

```bash
conda activate SentinelTest
```

### 3. Run Tests

```bash
# From project root
./scripts/run-tests.sh

# Or directly
cd backend/tests
pytest -v
```

## Environment Details

**Name:** `SentinelTest`

**Python Version:** 3.11

**Key Packages:**
- pytest>=7.4.0
- pytest-asyncio>=0.21.0
- httpx>=0.25.0
- selenium>=4.15.0 (for UI-based account activation)
- webdriver-manager>=4.0.0

## Prerequisites

### 1. Install Conda

If you don't have conda installed:

**macOS/Linux:**
```bash
# Download Miniconda
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
# Or for Linux:
# curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Install
bash Miniconda3-latest-*.sh

# Restart terminal or:
source ~/.bashrc  # or ~/.zshrc
```

**Windows:**
Download and install from: https://docs.conda.io/en/latest/miniconda.html

### 2. Services Running

Ensure required services are running:

```bash
docker-compose -f docker-compose.dev.yml up -d \
  keycloak iam_agent api_gateway postgres redis
```

### 3. Keycloak Configured

- Realm `agribotsai` exists
- Test user `admin@agribotsai.com` exists
- Account is activated (see `docs/archive/reference/identity/keycloak-account-activation.md`)

## Running Tests

### Using the Test Script (Recommended)

```bash
# From project root
./scripts/run-tests.sh

# Run specific test file
./scripts/run-tests.sh test_auth_flow_e2e.py

# Run with options
./scripts/run-tests.sh -v --tb=short test_auth_flow_e2e.py
```

### Manual Execution

```bash
# Activate environment
conda activate SentinelTest

# Set environment variables
export KEYCLOAK_URL=http://localhost:8081
export IAM_AGENT_URL=http://localhost:8005
export API_GATEWAY_URL=http://localhost:8082
export TEST_REALM=agribotsai
export TEST_CLIENT_ID=agribotsai-web
export TEST_USERNAME=admin@agribotsai.com
export TEST_PASSWORD=ChangeMe123!

# Run tests
cd backend/tests
pytest -v
```

## Environment Variables

Create a `.env` file in `backend/tests/` for convenience:

```bash
KEYCLOAK_URL=http://localhost:8081
IAM_AGENT_URL=http://localhost:8005
API_GATEWAY_URL=http://localhost:8082
TEST_REALM=agribotsai
TEST_CLIENT_ID=agribotsai-web
TEST_USERNAME=admin@agribotsai.com
TEST_PASSWORD=ChangeMe123!
```

## Updating the Environment

### Update from environment.yml

```bash
conda activate SentinelTest
conda env update -f backend/tests/environment.yml --prune
```

### Add New Package

```bash
conda activate SentinelTest
pip install <package-name>

# Update environment.yml to include it
```

## Troubleshooting

### Conda Command Not Found

**Solution:** 
1. Install Miniconda/Anaconda
2. Restart terminal
3. Or add conda to PATH: `export PATH="$HOME/miniconda3/bin:$PATH"`

### Environment Creation Fails

**Solution:**
```bash
# Try creating with explicit channel
conda create -n SentinelTest python=3.11 -y
conda activate SentinelTest
pip install -r backend/tests/requirements.txt
```

### Selenium Tests Fail

**Solution:**
```bash
# Install browser drivers
brew install chromedriver  # macOS
# Or let webdriver-manager handle it automatically

# Verify Selenium is installed
conda activate SentinelTest
python -c "import selenium; print(selenium.__version__)"
```

### Tests Fail: Services Not Available

**Solution:**
```bash
# Check services
docker-compose -f docker-compose.dev.yml ps

# Start services
docker-compose -f docker-compose.dev.yml up -d
```

## CI/CD Integration

For CI/CD pipelines, use conda in the test stage:

```yaml
# Example GitHub Actions
- name: Setup Conda
  uses: conda-incubator/setup-miniconda@v2
  with:
    environment-file: backend/tests/environment.yml
    activate-environment: SentinelTest

- name: Run Tests
  run: |
    conda activate SentinelTest
    pytest backend/tests -v
```

## Alternative: Virtual Environment

If conda is not available, you can use a standard Python virtual environment:

```bash
cd backend/tests
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
pytest -v
```

However, conda is recommended for better dependency management and cross-platform compatibility.

## Files

- `backend/tests/environment.yml` - Conda environment definition
- `backend/tests/setup-conda-env.sh` - Environment setup script
- `backend/tests/requirements.txt` - Python package requirements
- `scripts/run-tests.sh` - Test runner script with conda integration

## Next Steps

After setting up the environment:

1. Activate account: `./scripts/setup-test-account.sh`
2. Run tests: `./scripts/run-tests.sh`
3. Review test results and fix any failures

