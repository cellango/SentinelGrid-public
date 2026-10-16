#!/usr/bin/env python3
"""
Master Smoketest Runner for All Hero Flows

This script runs all test suites for all Hero Flows and ensures
they pass before release. This is CRITICAL - we cannot release
if any Hero Flow is broken.

Usage:
    python -m pytest backend/tests/smoketest.py -v
    python backend/tests/smoketest.py
"""

import sys
import subprocess
import os
from pathlib import Path
from typing import List, Tuple, Dict
import time

# Test suite files
HERO_FLOW_TEST_SUITES = {
    "Hero Flow 1": "backend/tests/test_hero_flow_1_suite.py",
    "Hero Flow 2": "backend/tests/test_hero_flow_2_suite.py",
    "Hero Flow 3": "backend/tests/test_hero_flow_3_suite.py",
    "Hero Flow 4": "backend/tests/test_hero_flow_4_suite.py",
    "Hero Flow 5": "backend/tests/test_hero_flow_5_suite.py",
}

# Additional test files that may exist
ADDITIONAL_TEST_FILES = {
    "Hero Flow 1 (SIEM Agent)": "backend/agents/siem_agent/tests/test_hero_flow_1.py",
    "Hero Flow 2 (Ticketing)": "backend/services/ticketing_agent/tests/test_hero_flow_2.py",
    "Hero Flow 4 & 5 (E2E)": "backend/tests/test_hero_flow_4_5_e2e.py",
    "Hero Flow 4 & 5 (Performance)": "backend/tests/test_hero_flow_4_5_performance.py",
    "Hero Flow 4 & 5 (Security)": "backend/tests/test_hero_flow_4_5_security.py",
}


def run_test_suite(suite_name: str, test_file: str) -> Tuple[bool, str, float]:
    """
    Run a single test suite and return results.
    
    Returns:
        (success: bool, output: str, duration: float)
    """
    if not os.path.exists(test_file):
        return False, f"Test file not found: {test_file}", 0.0
    
    start_time = time.time()
    
    try:
        # Run pytest on the test file
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                "-x",  # Stop on first failure
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per suite
        )
        
        duration = time.time() - start_time
        success = result.returncode == 0
        
        output = result.stdout + result.stderr
        
        return success, output, duration
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return False, f"Test suite timed out after {duration:.1f} seconds", duration
    except Exception as e:
        duration = time.time() - start_time
        return False, f"Error running test suite: {str(e)}", duration


def run_all_smoketests() -> Dict[str, Tuple[bool, str, float]]:
    """
    Run all Hero Flow test suites.
    
    Returns:
        Dictionary mapping suite names to (success, output, duration) tuples
    """
    results = {}
    
    print("=" * 80)
    print("SENTINELGRID SMOKETEST RUNNER")
    print("=" * 80)
    print()
    print("This smoketest validates all Hero Flows - our primary business flows.")
    print("CRITICAL: All tests must pass before release.")
    print()
    print(f"Running {len(HERO_FLOW_TEST_SUITES)} Hero Flow test suites...")
    print()
    
    # Run main test suites
    for suite_name, test_file in HERO_FLOW_TEST_SUITES.items():
        print(f"Running {suite_name}...")
        success, output, duration = run_test_suite(suite_name, test_file)
        results[suite_name] = (success, output, duration)
        
        if success:
            print(f"  ✅ {suite_name} PASSED ({duration:.1f}s)")
        else:
            print(f"  ❌ {suite_name} FAILED ({duration:.1f}s)")
        print()
    
    # Run additional test files if they exist
    print("Running additional test files...")
    print()
    
    for suite_name, test_file in ADDITIONAL_TEST_FILES.items():
        if os.path.exists(test_file):
            print(f"Running {suite_name}...")
            success, output, duration = run_test_suite(suite_name, test_file)
            results[suite_name] = (success, output, duration)
            
            if success:
                print(f"  ✅ {suite_name} PASSED ({duration:.1f}s)")
            else:
                print(f"  ❌ {suite_name} FAILED ({duration:.1f}s)")
            print()
    
    return results


def print_summary(results: Dict[str, Tuple[bool, str, float]]):
    """Print summary of test results."""
    print("=" * 80)
    print("SMOKETEST SUMMARY")
    print("=" * 80)
    print()
    
    total_suites = len(results)
    passed_suites = sum(1 for success, _, _ in results.values() if success)
    failed_suites = total_suites - passed_suites
    
    total_duration = sum(duration for _, _, duration in results.values())
    
    print(f"Total Test Suites: {total_suites}")
    print(f"Passed: {passed_suites}")
    print(f"Failed: {failed_suites}")
    print(f"Total Duration: {total_duration:.1f}s")
    print()
    
    if failed_suites > 0:
        print("FAILED TEST SUITES:")
        print("-" * 80)
        for suite_name, (success, output, duration) in results.items():
            if not success:
                print(f"  ❌ {suite_name} ({duration:.1f}s)")
                # Print first few lines of error output
                error_lines = output.split('\n')[:10]
                for line in error_lines:
                    if line.strip():
                        print(f"     {line}")
                print()
        print()
    
    print("=" * 80)
    
    if failed_suites == 0:
        print("✅ ALL SMOKETESTS PASSED - READY FOR RELEASE")
        print("=" * 80)
        return 0
    else:
        print("❌ SMOKETESTS FAILED - DO NOT RELEASE")
        print("=" * 80)
        print()
        print("CRITICAL: One or more Hero Flows are broken.")
        print("Please fix all failing tests before proceeding with release.")
        return 1


def main():
    """Main entry point for smoketest runner."""
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    # Run all test suites
    results = run_all_smoketests()
    
    # Print summary
    exit_code = print_summary(results)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

