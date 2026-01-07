#!/usr/bin/env python
"""
NEXOUS YAML 검증 테스트 스크립트
"""

import sys
from pathlib import Path

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from validator import validate_project_yaml, ProjectYAMLValidator

def test_valid_yaml():
    """유효한 YAML 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 1: Valid YAML")
    print("=" * 60)
    
    yaml_file = Path(__file__).parent / "schemas" / "sample_valid.yaml"
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = validate_project_yaml(content)
    
    print(f"\nResult: {'✓ PASS' if result.valid else '✗ FAIL'}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    print(f"Agents: {result.agents}")
    print(f"Artifacts: {result.artifacts}")
    
    if result.errors:
        print("\n[ERRORS]")
        for err in result.errors:
            print(f"  ✗ {err.field}: {err.message}")
    
    assert result.valid, "Valid YAML should pass"
    print("\n✓ Test passed!")


def test_invalid_yaml():
    """유효하지 않은 YAML 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 2: Invalid YAML")
    print("=" * 60)
    
    yaml_file = Path(__file__).parent / "schemas" / "sample_invalid.yaml"
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    result = validate_project_yaml(content)
    
    print(f"\nResult: {'✓ PASS' if result.valid else '✗ FAIL'}")
    print(f"Errors: {len(result.errors)}")
    
    print("\n[EXPECTED ERRORS]")
    for err in result.errors:
        print(f"  ✗ {err.field}: {err.message}")
    
    assert not result.valid, "Invalid YAML should fail"
    assert len(result.errors) > 0, "Should have errors"
    print("\n✓ Test passed! (correctly rejected invalid YAML)")


def test_circular_dependency():
    """순환 의존성 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 3: Circular Dependency")
    print("=" * 60)
    
    content = """
project:
  id: circular_test
  name: Circular Test
  domain: test

agents:
  - id: a
    preset: core/planner
    purpose: A
    dependencies:
      - c
  - id: b
    preset: core/executor
    purpose: B
    dependencies:
      - a
  - id: c
    preset: core/writer
    purpose: C
    dependencies:
      - b

execution:
  mode: sequential

trace:
  enabled: true
"""
    
    result = validate_project_yaml(content)
    
    print(f"\nResult: {'✓ PASS' if result.valid else '✗ FAIL'}")
    
    if result.errors:
        print("\n[ERRORS]")
        for err in result.errors:
            print(f"  ✗ {err.field}: {err.message}")
    
    # 순환 의존성 에러 확인
    circular_error = any("순환" in err.message for err in result.errors)
    assert circular_error, "Should detect circular dependency"
    print("\n✓ Test passed! (correctly detected circular dependency)")


def test_missing_required():
    """필수 필드 누락 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 4: Missing Required Fields")
    print("=" * 60)
    
    content = """
project:
  id: test
  name: Test
  # domain 누락
  
# agents 누락
# execution 누락
# trace 누락
"""
    
    result = validate_project_yaml(content)
    
    print(f"\nResult: {'✓ PASS' if result.valid else '✗ FAIL'}")
    print(f"Errors: {len(result.errors)}")
    
    print("\n[ERRORS]")
    for err in result.errors:
        print(f"  ✗ {err.field}: {err.message}")
    
    assert not result.valid, "Should fail for missing required fields"
    print("\n✓ Test passed!")


def main():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("  NEXOUS YAML Validator Tests")
    print("=" * 60)
    
    try:
        test_valid_yaml()
        test_invalid_yaml()
        test_circular_dependency()
        test_missing_required()
        
        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED! ✓")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
