# SPEC-021 구현 계획서

## 1. 개요

| 항목 | 값 |
|------|-----|
| **SPEC ID** | SPEC-021 |
| **제목** | React Flow Canvas - ReactFlow 기반 워크플로우 편집기 |
| **예상 소요 시간** | 8-12시간 |
| **우선순위** | HIGH |
| **작성일** | 2026-01-15 |

---

## 2. 구현 단계

### Phase 1: 기반 설정 (2시간)

#### Task 1.1: 의존성 설치

```bash
cd frontend
pnpm add reactflow zustand uuid
pnpm add -D @types/uuid
```

#### Task 1.2: Zustand 스토어 생성

**파일**: `frontend/stores/workflow-store.ts`

```typescript
// 구현 내용:
// - nodes, edges 상태
// - onNodesChange, onEdgesChange, onConnect 핸들러
// - addNode, updateNodeData, removeNode 액션
// - loadWorkflow, clearWorkflow, exportWorkflow 유틸리티
```

#### Task 1.3: 노드 타입 정의

**파일**: `frontend/types/workflow.ts`

```typescript
// 노드 타입 열거형
// 노드 데이터 인터페이스
// 엣지 데이터 인터페이스
```

---

### Phase 2: 커스텀 노드 구현 (3시간)

#### Task 2.1: BaseNode 컴포넌트

**파일**: `frontend/components/workflow/nodes/BaseNode.tsx`

- 공통 노드 래퍼 컴포넌트
- 선택 상태 스타일링
- 노드 타입별 색상 배지

#### Task 2.2: 6가지 노드 컴포넌트

| 파일 | 설명 |
|------|------|
| `TriggerNode.tsx` | 출력 핸들 1개, 트리거 타입 선택 UI |
| `ToolNode.tsx` | 입출력 핸들 각 1개, 도구 선택 드롭다운 |
| `AgentNode.tsx` | 입출력 핸들 각 1개, 프롬프트 미리보기 |
| `ConditionNode.tsx` | 입력 1개, 동적 출력 핸들, 조건식 편집 |
| `AdapterNode.tsx` | 입출력 핸들 각 1개, 타입 매핑 UI |
| `AggregatorNode.tsx` | 동적 입력 핸들, 출력 1개, 집계 설정 |

#### Task 2.3: 노드 타입 레지스트리

**파일**: `frontend/components/workflow/nodes/index.ts`

```typescript
export const nodeTypes = {
  trigger: TriggerNode,
  tool: ToolNode,
  agent: AgentNode,
  condition: ConditionNode,
  adapter: AdapterNode,
  aggregator: AggregatorNode,
};
```

---

### Phase 3: 캔버스 및 에디터 구현 (2시간)

#### Task 3.1: WorkflowCanvas 컴포넌트

**파일**: `frontend/components/workflow/WorkflowCanvas.tsx`

- ReactFlow 컴포넌트 래핑
- nodeTypes 등록
- Background, Controls, MiniMap 포함
- 연결 검증 로직 (순환 참조 방지)

#### Task 3.2: NodePalette 컴포넌트

**파일**: `frontend/components/workflow/NodePalette.tsx`

- 6가지 노드 타입 목록
- 드래그 시작 이벤트 핸들링
- 노드 타입별 아이콘 및 설명

#### Task 3.3: WorkflowEditor 컴포넌트

**파일**: `frontend/components/workflow/WorkflowEditor.tsx`

- 레이아웃: 사이드바(Palette) + 캔버스
- 드롭 이벤트 핸들링 (노드 생성)
- 키보드 단축키 (Delete, Ctrl+Z 등)

---

### Phase 4: 페이지 통합 (1시간)

#### Task 4.1: 워크플로우 편집 페이지

**파일**: `frontend/app/workflows/[id]/page.tsx`

- WorkflowEditor 컴포넌트 통합
- 워크플로우 로드/저장 로직
- 헤더 (워크플로우 이름, 저장 버튼)

---

### Phase 5: 테스트 및 검증 (2시간)

#### Task 5.1: 단위 테스트

- Zustand 스토어 액션 테스트
- 순환 참조 검증 로직 테스트

#### Task 5.2: 통합 테스트

- 노드 생성/삭제 시나리오
- 연결 생성/삭제 시나리오
- 드래그앤드롭 시나리오

---

## 3. 파일 구조

```
frontend/
├── components/
│   └── workflow/
│       ├── WorkflowEditor.tsx        # 메인 에디터 (레이아웃)
│       ├── WorkflowCanvas.tsx        # ReactFlow 캔버스
│       ├── NodePalette.tsx           # 노드 팔레트 사이드바
│       ├── NodePropertiesPanel.tsx   # 노드 속성 편집 패널
│       └── nodes/
│           ├── index.ts              # nodeTypes 등록
│           ├── BaseNode.tsx          # 공통 노드 래퍼
│           ├── TriggerNode.tsx
│           ├── ToolNode.tsx
│           ├── AgentNode.tsx
│           ├── ConditionNode.tsx
│           ├── AdapterNode.tsx
│           └── AggregatorNode.tsx
├── stores/
│   └── workflow-store.ts             # Zustand 워크플로우 스토어
├── types/
│   └── workflow.ts                   # 타입 정의
├── lib/
│   └── workflow/
│       └── validation.ts             # DAG 검증 유틸리티
└── app/
    └── workflows/
        └── [id]/
            └── page.tsx              # 워크플로우 편집 페이지
```

---

## 4. 의존성

### 4.1 신규 패키지

| 패키지 | 버전 | 용도 |
|--------|------|------|
| `reactflow` | ^11.10.0 | 노드 기반 에디터 라이브러리 |
| `zustand` | ^5.0.0 | 상태 관리 |
| `uuid` | ^9.0.0 | 노드 UUID 생성 |

### 4.2 기존 활용 패키지

- `tailwindcss` - 스타일링
- `@radix-ui/*` (shadcn/ui) - UI 컴포넌트

---

## 5. 리스크 분석

| 리스크 | 영향도 | 발생 확률 | 대응 방안 |
|--------|--------|-----------|-----------|
| ReactFlow 버전 호환성 | 중 | 낮음 | 공식 문서 기준 구현, 마이너 버전 고정 |
| 대량 노드 성능 저하 | 중 | 중간 | 가상화, 청크 렌더링 적용 |
| Zustand 상태 동기화 이슈 | 낮음 | 낮음 | immer 미들웨어 활용 |

---

## 6. 검증 기준

### 6.1 기능 완성 체크리스트

- [ ] 6가지 노드 타입 모두 렌더링 가능
- [ ] 드래그앤드롭으로 노드 생성 가능
- [ ] 노드 간 연결(엣지) 생성 가능
- [ ] 순환 참조 연결 차단 동작
- [ ] 노드 선택 시 속성 패널 표시
- [ ] Delete 키로 노드/엣지 삭제 가능
- [ ] 미니맵, 줌, 팬 컨트롤 동작
- [ ] Zustand 스토어와 UI 동기화

### 6.2 품질 기준

- TypeScript strict 모드 오류 없음
- ESLint 경고/오류 없음
- 테스트 커버리지 80% 이상

---

## 7. 일정

| 단계 | 예상 시간 | 누적 |
|------|-----------|------|
| Phase 1: 기반 설정 | 2시간 | 2시간 |
| Phase 2: 커스텀 노드 | 3시간 | 5시간 |
| Phase 3: 캔버스/에디터 | 2시간 | 7시간 |
| Phase 4: 페이지 통합 | 1시간 | 8시간 |
| Phase 5: 테스트/검증 | 2시간 | 10시간 |
| 버퍼 | 2시간 | 12시간 |

**총 예상 소요**: 8-12시간
