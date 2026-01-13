# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SPEC-005: Execution Tracking Models 구현 완료
  - WorkflowExecution 모델: 워크플로우 실행 인스턴스 추적
  - NodeExecution 모델: 개별 노드 실행 상태 추적
  - ExecutionLog 모델: 실행 로그 저장
  - Alembic 마이그레이션: 002_phase2_execution_models.py
  - 113개 테스트 통과, 91.71% 커버리지

### Changed
- Phase 2 상태 변경: 실행 추적 모델 완료

## [0.1.0] - 2026-01-12

### Added
- SPEC-001: Database Foundation Setup
- SPEC-002: User Authentication Model
- SPEC-003: Workflow Domain Models
- SPEC-007: Workflow Execution Engine

---

## Specification Version Format

- `[Unreleased]`: 아직 릴리스되지 않은 변경사항
- `[Version]`: 릴리스된 버전 (YYYY-MM-DD)

### Change Types
- **Added**: 새로운 기능
- **Changed**: 기존 기능의 변경
- **Deprecated**: 향후 제거될 기능
- **Removed**: 제거된 기능
- **Fixed**: 버그 수정
- **Security**: 보안 관련 변경
