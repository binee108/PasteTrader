# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SPEC-011: Workflow Execution Engine 구현 진행 중
  - WorkflowExecutor: DAG 기반 비동기 실행 엔진 (317 lines, 71.56% 커버리지)
  - ExecutionContext: 노드 간 데이터 전달 컨텍스트 (157 lines, 100% 커버리지)
  - Execution 예외 클래스: NodeTimeoutError, NodeExecutionError, ExecutionCancelledError 등 (203 lines, 100% 커버리지)
  - asyncio.TaskGroup 기반 병렬 실행, 지수 백오프 재시도, 실패 격리 정책
  - 189개 테스트 전체 통과 (REQ-011-001~005, 007~011 완료, REQ-011-006는 SPEC-012로 이관)
- SPEC-009: Tool/Agent API Endpoints 구현 완료
  - Tool API: 7개 엔드포인트 (생성, 목록, 상세, 수정, 삭제, 테스트)
  - Agent API: 6개 엔드포인트 (생성, 목록, 상세, 수정, 삭제, 도구 연결, 테스트)
  - ToolService 및 AgentService 비즈니스 로직 계층 구현
  - 28개 보안 테스트 통과, 100% 테스트 커버리지
  - mypy 타입 체크 0 에러
- SPEC-005: Execution Tracking Models 구현 완료
  - WorkflowExecution 모델: 워크플로우 실행 인스턴스 추적
  - NodeExecution 모델: 개별 노드 실행 상태 추적
  - ExecutionLog 모델: 실행 로그 저장
  - Alembic 마이그레이션: 002_phase2_execution_models.py
  - 113개 테스트 통과, 91.71% 커버리지

### Changed
- Phase 2 상태 변경: 실행 추적 모델 완료
- 보안 모듈 개선: passlib 대신 직접 bcrypt 사용
- 타입 어노테이션 수정: AsyncGenerator 타입 수정
- 모델 구조 통합: is_active 필드를 SoftDeleteMixin으로 이동

### Removed
- passlib 의존성 제거 (pyproject.toml)

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
