# Detection Service Tests

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


## Overview

This directory contains tests for the Detection Service, including:
- Unit tests for individual detection rules
- Unit tests for the rule engine
- Integration tests for API endpoints
- Tests for the scheduler functionality

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-mock httpx
```

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Files

```bash
# Test rules only
pytest tests/test_rules.py

# Test rule engine only
pytest tests/test_rule_engine.py

# Test integration only
pytest tests/test_integration.py

# Test scheduler only
pytest tests/test_scheduler.py
```

### Run with Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

## Test Structure

- `conftest.py`: Shared fixtures (database session, test rules, sample events)
- `test_rules.py`: Unit tests for individual detection rules
- `test_rule_engine.py`: Unit tests for rule engine evaluation logic
- `test_integration.py`: Integration tests for API endpoints
- `test_scheduler.py`: Tests for background scheduler functionality

## Mocking

Tests use mocks for:
- SIEM Agent API calls (event fetching)
- Alert creation service
- IAM Agent token validation
- Database sessions

## Test Database

Tests use SQLite in-memory database by default (fast, isolated tests).

To use PostgreSQL for tests:
```bash
export TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db
pytest tests/
```

