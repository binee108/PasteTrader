# Paste Trader - Technology Stack

## 기술 스택 개요

| 계층 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **Frontend** | Next.js | 15.x | React 기반 풀스택 프레임워크 |
| | TailwindCSS | 3.4.x | 유틸리티 기반 CSS |
| | shadcn/ui | latest | 재사용 가능 UI 컴포넌트 |
| **Backend API** | FastAPI | 0.115.x | 고성능 Python API 프레임워크 |
| | Pydantic | 2.10.x | 데이터 검증 및 직렬화 |
| | SQLAlchemy | 2.0.x | ORM |
| **Meta LLM** | Python | 3.13.x | ReAct 패턴 구현 |
| | anthropic | 0.45.x | Claude API 클라이언트 |
| | openai | 1.60.x | OpenAI API 클라이언트 |
| **코드 분석** | grep | system | 텍스트 검색 |
| | ast-grep | 0.34.x | 구조적 코드 검색 |
| **Workflow** | Python | 3.13.x | 직접 구현 (n8n 스타일) |
| | PyYAML | 6.0.x | YAML 파싱 |
| **Database** | PostgreSQL | 16.x | 메인 데이터베이스 |
| **Cache** | Redis | 7.4.x | 캐싱 및 실시간 데이터 |
| **Scheduler** | APScheduler | 3.11.x | 정기 작업 스케줄링 |
| **Package Manager** | uv | 0.5.x | Python 패키지 관리 |
| | pnpm | 9.x | Node.js 패키지 관리 |

---

## Frontend 기술 상세

### Next.js 15 설정

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.githubusercontent.com',
      },
    ],
  },
};

export default config;
```

### TailwindCSS 설정

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        // ... trading specific colors
        bullish: "hsl(var(--bullish))",
        bearish: "hsl(var(--bearish))",
        neutral: "hsl(var(--neutral))",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

### 주요 프론트엔드 라이브러리

| 라이브러리 | 버전 | 용도 |
|------------|------|------|
| `@tanstack/react-query` | 5.64.x | 서버 상태 관리 |
| `zustand` | 5.0.x | 클라이언트 상태 관리 |
| `reactflow` | 11.10.x | 워크플로우 시각화 (노드 기반 에디터) |
| `recharts` | 2.15.x | 차트 렌더링 |
| `zod` | 3.24.x | 스키마 검증 |
| `date-fns` | 4.1.x | 날짜 유틸리티 |
| `pdfjs-dist` | 4.8.x | PDF 파싱 |
| `youtube-transcript` | 1.2.x | YouTube 자막 추출 |

---

## 워크플로우 시각화 (React Flow) 상세

### React Flow 설정

```tsx
// components/workflow/WorkflowCanvas.tsx
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Node,
  Edge,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { ToolNode } from './nodes/ToolNode';
import { AgentNode } from './nodes/AgentNode';
import { ConditionNode } from './nodes/ConditionNode';
import { AdapterNode } from './nodes/AdapterNode';
import { TriggerNode } from './nodes/TriggerNode';

// 커스텀 노드 타입 등록
const nodeTypes = {
  trigger: TriggerNode,
  tool: ToolNode,
  agent: AgentNode,
  condition: ConditionNode,
  adapter: AdapterNode,
};

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

### 커스텀 노드 구현 예시

```tsx
// components/workflow/nodes/ToolNode.tsx
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface ToolNodeData {
  label: string;
  toolId: string;
  description?: string;
  config?: Record<string, unknown>;
}

export const ToolNode = memo(({ data, selected }: NodeProps<ToolNodeData>) => {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white shadow-sm min-w-[180px]
        ${selected ? 'border-blue-500' : 'border-gray-200'}
      `}
    >
      {/* 입력 포트 (왼쪽) */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-blue-500"
      />

      {/* 노드 헤더 */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
          Tool
        </span>
        <span className="font-medium text-sm">{data.label}</span>
      </div>

      {/* 노드 설명 */}
      {data.description && (
        <p className="text-xs text-gray-500">{data.description}</p>
      )}

      {/* 출력 포트 (오른쪽) */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-blue-500"
      />
    </div>
  );
});

ToolNode.displayName = 'ToolNode';
```

### 조건 분기 노드 (다중 출력)

```tsx
// components/workflow/nodes/ConditionNode.tsx
import { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

interface ConditionNodeData {
  label: string;
  conditions: Array<{
    id: string;
    name: string;
    expression: string;
  }>;
}

export const ConditionNode = memo(({ data, selected }: NodeProps<ConditionNodeData>) => {
  return (
    <div
      className={`
        px-4 py-3 rounded-lg border-2 bg-white shadow-sm min-w-[200px]
        ${selected ? 'border-purple-500' : 'border-gray-200'}
      `}
    >
      {/* 입력 포트 */}
      <Handle type="target" position={Position.Left} />

      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
          Condition
        </span>
        <span className="font-medium text-sm">{data.label}</span>
      </div>

      {/* 다중 출력 포트 */}
      <div className="space-y-2">
        {data.conditions.map((condition, index) => (
          <div key={condition.id} className="flex items-center justify-between">
            <span className="text-xs text-gray-600">{condition.name}</span>
            <Handle
              type="source"
              position={Position.Right}
              id={condition.id}
              style={{ top: `${30 + index * 24}px` }}
              className="w-3 h-3 bg-purple-500"
            />
          </div>
        ))}
      </div>
    </div>
  );
});

ConditionNode.displayName = 'ConditionNode';
```

### Zustand 워크플로우 스토어

```typescript
// stores/workflow-store.ts
import { create } from 'zustand';
import {
  Node,
  Edge,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  NodeChange,
  EdgeChange,
  Connection,
} from 'reactflow';

interface WorkflowState {
  // State
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;

  // Actions
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;

  // Node operations
  addNode: (type: string, position: { x: number; y: number }, data: any) => void;
  updateNodeData: (nodeId: string, data: Partial<any>) => void;
  removeNode: (nodeId: string) => void;

  // Edge operations
  removeEdge: (edgeId: string) => void;

  // Selection
  setSelectedNode: (nodeId: string | null) => void;

  // Workflow operations
  loadWorkflow: (nodes: Node[], edges: Edge[]) => void;
  clearWorkflow: () => void;
  exportWorkflow: () => { nodes: Node[]; edges: Edge[] };
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  // Initial state
  nodes: [],
  edges: [],
  selectedNodeId: null,

  // React Flow change handlers
  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
    });
  },

  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },

  onConnect: (connection) => {
    set({
      edges: addEdge(connection, get().edges),
    });
  },

  // Node operations
  addNode: (type, position, data) => {
    const newNode: Node = {
      id: `${type}-${Date.now()}`,
      type,
      position,
      data,
    };
    set({
      nodes: [...get().nodes, newNode],
    });
  },

  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...data } }
          : node
      ),
    });
  },

  removeNode: (nodeId) => {
    set({
      nodes: get().nodes.filter((node) => node.id !== nodeId),
      edges: get().edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ),
    });
  },

  // Edge operations
  removeEdge: (edgeId) => {
    set({
      edges: get().edges.filter((edge) => edge.id !== edgeId),
    });
  },

  // Selection
  setSelectedNode: (nodeId) => {
    set({ selectedNodeId: nodeId });
  },

  // Workflow operations
  loadWorkflow: (nodes, edges) => {
    set({ nodes, edges });
  },

  clearWorkflow: () => {
    set({ nodes: [], edges: [], selectedNodeId: null });
  },

  exportWorkflow: () => {
    const { nodes, edges } = get();
    return { nodes, edges };
  },
}));
```

### Zustand 스토어와 React Flow 연동

```tsx
// components/workflow/WorkflowEditor.tsx
import { useCallback } from 'react';
import ReactFlow, { Controls, Background, MiniMap } from 'reactflow';
import { useWorkflowStore } from '@/stores/workflow-store';

export function WorkflowEditor() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    setSelectedNode,
  } = useWorkflowStore();

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node.id);
    },
    [setSelectedNode]
  );

  const handlePaneClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onPaneClick={handlePaneClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

---

## 입력 소스 처리

### 텍스트 입력 컴포넌트

```tsx
// components/paste-input/TextPasteInput.tsx
import { useState } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

interface TextPasteInputProps {
  onSubmit: (text: string) => void;
  isLoading?: boolean;
}

export function TextPasteInput({ onSubmit, isLoading }: TextPasteInputProps) {
  const [text, setText] = useState('');

  return (
    <div className="space-y-4">
      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="트레이딩 방법론을 붙여넣기하세요..."
        className="min-h-[200px]"
      />
      <Button
        onClick={() => onSubmit(text)}
        disabled={!text.trim() || isLoading}
      >
        {isLoading ? '분석 중...' : '워크플로우 생성'}
      </Button>
    </div>
  );
}
```

### PDF 파싱 (백엔드)

```python
# backend/app/services/parsers/pdf_parser.py
import pdfplumber
from io import BytesIO


async def parse_pdf(file_content: bytes) -> str:
    """PDF 파일에서 텍스트 추출."""
    text_content = []

    with pdfplumber.open(BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)

    return "\n\n".join(text_content)
```

### YouTube 자막 추출 (백엔드)

```python
# backend/app/services/parsers/youtube_parser.py
from youtube_transcript_api import YouTubeTranscriptApi
import re


def extract_video_id(url: str) -> str:
    """YouTube URL에서 비디오 ID 추출."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Invalid YouTube URL")


async def get_youtube_transcript(url: str) -> str:
    """YouTube 영상의 자막 추출."""
    video_id = extract_video_id(url)

    # 한국어 자막 우선, 없으면 영어
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    try:
        transcript = transcript_list.find_transcript(['ko', 'en'])
    except:
        transcript = transcript_list.find_generated_transcript(['ko', 'en'])

    entries = transcript.fetch()
    return " ".join([entry['text'] for entry in entries])
```

---

## Backend API 기술 상세

### FastAPI 설정

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Paste Trader API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")
```

### 주요 백엔드 라이브러리

| 라이브러리 | 버전 | 용도 |
|------------|------|------|
| `uvicorn` | 0.34.x | ASGI 서버 |
| `asyncpg` | 0.30.x | PostgreSQL 비동기 드라이버 |
| `redis` | 5.2.x | Redis 클라이언트 |
| `httpx` | 0.28.x | HTTP 클라이언트 |
| `pydantic-settings` | 2.7.x | 환경 설정 관리 |

### 프로젝트 설정 (pyproject.toml)

```toml
[project]
name = "paste-trader"
version = "0.1.0"
description = "AI-powered trading workflow automation platform"
requires-python = ">=3.13"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "sqlalchemy>=2.0.0",
    "asyncpg>=0.30.0",
    "redis>=5.2.0",
    "httpx>=0.28.0",
    "apscheduler>=3.11.0",
    "pyyaml>=6.0.0",
    # LLM Providers
    "anthropic>=0.45.0",
    "openai>=1.60.0",
    # Code Analysis
    # ast-grep installed via binary
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.9.0",
    "mypy>=1.14.0",
]

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## LLM Provider 아키텍처

### Multi-Provider 설계

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Client Architecture                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                      LLMClient                          │ │
│  │  - route_by_purpose(purpose: Purpose) -> Provider      │ │
│  │  - get_provider(name: str) -> Provider                 │ │
│  │  - execute(provider: str, prompt: str) -> Response     │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  ProviderRegistry                       │ │
│  │  - providers: Dict[str, ProviderConfig]                │ │
│  │  - purpose_mapping: Dict[Purpose, str]                 │ │
│  │  - register(name: str, config: ProviderConfig)         │ │
│  │  - get(name: str) -> ProviderConfig                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Anthropic   │  │   OpenAI    │  │   Z.AI GLM  │         │
│  │ Provider    │  │  Provider   │  │  Provider   │         │
│  │             │  │             │  │             │         │
│  │ - claude-*  │  │ - gpt-4o    │  │ - glm-4     │         │
│  │ - opus/     │  │ - gpt-4-*   │  │ - glm-4-*   │         │
│  │   sonnet    │  │ - o1/o3     │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│           │               │               │                 │
│           └───────────────┼───────────────┘                 │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                  ProviderFactory                        │ │
│  │  - create(config: ProviderConfig) -> BaseProvider      │ │
│  │  - validate_credentials(config) -> bool                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4가지 인증 모드

```python
# meta_llm/providers/base.py
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel


class AuthMode(str, Enum):
    OAUTH = "oauth"          # OAuth 2.0 flow
    STANDALONE = "standalone" # Direct API key
    SDK = "sdk"              # SDK-based auth
    GLM = "glm"              # Z.AI GLM specific


class ProviderConfig(BaseModel):
    name: str
    auth_mode: AuthMode
    api_key: str | None = None
    oauth_config: dict | None = None
    sdk_config: dict | None = None
    glm_config: dict | None = None

    # Model settings
    default_model: str
    available_models: list[str]

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 100000


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ) -> str:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ):
        pass
```

### Provider 설정 (YAML)

```yaml
# config/providers.yaml
providers:
  anthropic:
    name: Anthropic
    auth_mode: standalone
    api_key: "${ANTHROPIC_API_KEY}"
    default_model: claude-sonnet-4-20250514
    available_models:
      - claude-sonnet-4-20250514
      - claude-opus-4-20250514
    rate_limits:
      requests_per_minute: 50
      tokens_per_minute: 80000
    pricing:
      input_per_1m: 3.00   # USD per 1M tokens
      output_per_1m: 15.00

  openai:
    name: OpenAI
    auth_mode: standalone
    api_key: "${OPENAI_API_KEY}"
    default_model: gpt-4o
    available_models:
      - gpt-4o
      - gpt-4o-mini
      - o1
      - o3-mini
    rate_limits:
      requests_per_minute: 60
      tokens_per_minute: 150000
    pricing:
      input_per_1m: 2.50
      output_per_1m: 10.00

  glm:
    name: Z.AI GLM
    auth_mode: glm
    glm_config:
      endpoint: "https://open.bigmodel.cn/api/paas/v4"
      token: "${ZAI_GLM_TOKEN}"
    default_model: glm-4-plus
    available_models:
      - glm-4-plus
      - glm-4-flash
      - glm-4-long
    rate_limits:
      requests_per_minute: 100
      tokens_per_minute: 200000
    pricing:
      input_per_1m: 0.50
      output_per_1m: 0.50

# Purpose-based routing
purpose_mapping:
  meta_llm: anthropic           # Complex reasoning
  agent_reasoning: anthropic    # Agent decision making
  fast_analysis: openai         # Quick analysis tasks
  bulk_processing: glm          # High volume, cost-effective
  code_generation: anthropic    # Code generation
  summarization: glm            # Text summarization
```

### 용도별 제공자 라우팅

```python
# meta_llm/providers/router.py
from enum import Enum
from typing import Optional

from .base import BaseProvider
from .registry import ProviderRegistry


class Purpose(str, Enum):
    META_LLM = "meta_llm"               # Main reasoning
    AGENT_REASONING = "agent_reasoning"  # Agent decisions
    FAST_ANALYSIS = "fast_analysis"      # Quick tasks
    BULK_PROCESSING = "bulk_processing"  # High volume
    CODE_GENERATION = "code_generation"  # Code tasks
    SUMMARIZATION = "summarization"      # Text summary


class ProviderRouter:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def route(
        self,
        purpose: Purpose,
        override_provider: Optional[str] = None
    ) -> BaseProvider:
        """Route to appropriate provider based on purpose."""
        if override_provider:
            return self.registry.get(override_provider)

        provider_name = self.registry.purpose_mapping.get(purpose)
        if not provider_name:
            raise ValueError(f"No provider configured for purpose: {purpose}")

        return self.registry.get(provider_name)

    async def execute(
        self,
        purpose: Purpose,
        messages: list[dict],
        **kwargs
    ) -> str:
        """Execute with automatic provider routing."""
        provider = self.route(purpose)
        return await provider.complete(messages, **kwargs)
```

### Provider 구현 예시

```python
# meta_llm/providers/anthropic.py
from anthropic import AsyncAnthropic

from .base import BaseProvider, ProviderConfig


class AnthropicProvider(BaseProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncAnthropic(api_key=config.api_key)

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ) -> str:
        model = model or self.config.default_model

        response = await self.client.messages.create(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        )

        return response.content[0].text

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs
    ):
        model = model or self.config.default_model

        async with self.client.messages.stream(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
        ) as stream:
            async for text in stream.text_stream:
                yield text
```

---

## Meta LLM 엔진 상세

### ReAct 패턴 구현

```python
# meta_llm/core/react_controller.py
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from ..providers.router import ProviderRouter, Purpose
from ..tools.registry import ToolRegistry


class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"


@dataclass
class ReActStep:
    step_type: StepType
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[Any] = None


class ReActController:
    """
    ReAct (Reasoning + Acting) pattern controller.

    Implements the loop:
    1. Thought - Analyze current state, plan next action
    2. Action - Execute tool or delegate to agent
    3. Observation - Collect and evaluate results
    4. Repeat until goal is achieved
    """

    def __init__(
        self,
        provider_router: ProviderRouter,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
    ):
        self.router = provider_router
        self.tools = tool_registry
        self.max_iterations = max_iterations

    async def run(
        self,
        goal: str,
        context: Optional[dict] = None,
    ) -> list[ReActStep]:
        """Execute ReAct loop until goal is achieved."""
        steps: list[ReActStep] = []
        context = context or {}

        for i in range(self.max_iterations):
            # 1. Thought
            thought = await self._think(goal, steps, context)
            steps.append(thought)

            if thought.step_type == StepType.FINAL:
                break

            # 2. Action
            action = await self._act(thought)
            steps.append(action)

            # 3. Observation
            observation = await self._observe(action)
            steps.append(observation)

            # Update context with observation
            context["last_observation"] = observation.content

        return steps

    async def _think(
        self,
        goal: str,
        history: list[ReActStep],
        context: dict,
    ) -> ReActStep:
        """Generate thought about next action."""
        prompt = self._build_thought_prompt(goal, history, context)

        response = await self.router.execute(
            purpose=Purpose.META_LLM,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        return self._parse_thought(response)

    async def _act(self, thought: ReActStep) -> ReActStep:
        """Execute the planned action."""
        if not thought.tool_name:
            raise ValueError("Thought must specify a tool")

        tool = self.tools.get(thought.tool_name)
        result = await tool.execute(thought.tool_input or {})

        return ReActStep(
            step_type=StepType.ACTION,
            content=f"Executed {thought.tool_name}",
            tool_name=thought.tool_name,
            tool_input=thought.tool_input,
            tool_output=result,
        )

    async def _observe(self, action: ReActStep) -> ReActStep:
        """Process and summarize action results."""
        return ReActStep(
            step_type=StepType.OBSERVATION,
            content=str(action.tool_output),
        )
```

### 도구 레지스트리

```python
# meta_llm/tools/registry.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Type


class BaseTool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema

    @abstractmethod
    async def execute(self, params: dict) -> Any:
        pass


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_all(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in self._tools.values()
        ]
```

### grep/ast-grep 래퍼

```python
# meta_llm/tools/code_analyzer.py
import asyncio
import json
from typing import Optional

from .registry import BaseTool


class GrepTool(BaseTool):
    name = "grep"
    description = "Search for text patterns in files using grep"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Search pattern (regex)"},
            "path": {"type": "string", "description": "Directory to search"},
            "file_types": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["pattern"],
    }

    async def execute(self, params: dict) -> dict:
        pattern = params["pattern"]
        path = params.get("path", ".")
        file_types = params.get("file_types", [])

        cmd = ["grep", "-rn", pattern, path]
        if file_types:
            for ft in file_types:
                cmd.extend(["--include", f"*.{ft}"])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        return {
            "matches": stdout.decode().split("\n") if stdout else [],
            "error": stderr.decode() if stderr else None,
        }


class AstGrepTool(BaseTool):
    name = "ast_grep"
    description = "Search for code patterns using AST-based matching"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "AST pattern to match"},
            "language": {"type": "string", "description": "Programming language"},
            "path": {"type": "string", "description": "Directory to search"},
        },
        "required": ["pattern", "language"],
    }

    async def execute(self, params: dict) -> dict:
        pattern = params["pattern"]
        language = params["language"]
        path = params.get("path", ".")

        cmd = [
            "sg", "scan",
            "--pattern", pattern,
            "--lang", language,
            "--json",
            path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if stdout:
            return {"matches": json.loads(stdout.decode())}
        return {"matches": [], "error": stderr.decode() if stderr else None}
```

---

## 워크플로우 엔진 상세

### DAG 실행기

```python
# workflow_engine/core/executor.py
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import asyncio

from .dag import DAG
from .node import Node, NodeResult


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class NodeExecution:
    node_id: str
    status: ExecutionStatus
    result: Optional[NodeResult] = None
    error: Optional[str] = None


class DAGExecutor:
    """Execute DAG workflows with proper dependency handling."""

    def __init__(self, dag: DAG):
        self.dag = dag
        self.executions: Dict[str, NodeExecution] = {}
        self.context: Dict[str, Any] = {}

    async def run(self) -> Dict[str, NodeExecution]:
        """Execute all nodes in dependency order."""
        # Initialize all executions as pending
        for node_id in self.dag.nodes:
            self.executions[node_id] = NodeExecution(
                node_id=node_id,
                status=ExecutionStatus.PENDING,
            )

        # Get execution order (topological sort)
        execution_order = self.dag.topological_sort()

        for level in execution_order:
            # Execute all nodes in current level in parallel
            await asyncio.gather(*[
                self._execute_node(node_id)
                for node_id in level
            ])

        return self.executions

    async def _execute_node(self, node_id: str) -> None:
        """Execute a single node."""
        node = self.dag.get_node(node_id)
        execution = self.executions[node_id]

        # Check dependencies
        if not self._dependencies_satisfied(node):
            execution.status = ExecutionStatus.SKIPPED
            return

        execution.status = ExecutionStatus.RUNNING

        try:
            # Gather inputs from dependencies
            inputs = self._gather_inputs(node)

            # Execute node
            result = await node.execute(inputs, self.context)

            execution.status = ExecutionStatus.COMPLETED
            execution.result = result

            # Store outputs in context
            self.context[node_id] = result.outputs

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)

    def _dependencies_satisfied(self, node: Node) -> bool:
        """Check if all dependencies are completed."""
        for dep_id in node.depends_on:
            if self.executions[dep_id].status != ExecutionStatus.COMPLETED:
                return False
        return True

    def _gather_inputs(self, node: Node) -> Dict[str, Any]:
        """Gather inputs from dependency outputs."""
        inputs = {}
        for dep_id in node.depends_on:
            inputs[dep_id] = self.context.get(dep_id, {})
        return inputs
```

### 스케줄러 통합

```python
# workflow_engine/scheduler/apscheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional


class WorkflowScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs = {}

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        self.scheduler.shutdown()

    def schedule_workflow(
        self,
        workflow_id: str,
        cron: str,
        callback: Callable,
        timezone: str = "Asia/Seoul",
    ) -> str:
        """Schedule a workflow to run on cron expression."""
        trigger = CronTrigger.from_crontab(cron, timezone=timezone)

        job = self.scheduler.add_job(
            callback,
            trigger=trigger,
            id=workflow_id,
            kwargs={"workflow_id": workflow_id},
        )

        self._jobs[workflow_id] = job
        return job.id

    def unschedule_workflow(self, workflow_id: str) -> None:
        """Remove a scheduled workflow."""
        if workflow_id in self._jobs:
            self.scheduler.remove_job(workflow_id)
            del self._jobs[workflow_id]

    def get_next_run(self, workflow_id: str) -> Optional[str]:
        """Get next scheduled run time."""
        if workflow_id in self._jobs:
            job = self._jobs[workflow_id]
            return str(job.next_run_time)
        return None
```

---

## 데이터베이스 설계

### PostgreSQL 스키마

```sql
-- Workflows
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    yaml_content TEXT NOT NULL,
    version VARCHAR(50) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow Executions
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    context JSONB,
    error_message TEXT
);

-- Node Executions
CREATE TABLE node_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_execution_id UUID REFERENCES workflow_executions(id),
    node_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    inputs JSONB,
    outputs JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Tools
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    parameters JSONB NOT NULL,
    implementation_path VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    system_prompt TEXT NOT NULL,
    model_config JSONB NOT NULL,
    tool_ids UUID[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schedules
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    cron_expression VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Asia/Seoul',
    is_active BOOLEAN DEFAULT true,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_executions_workflow ON workflow_executions(workflow_id);
CREATE INDEX idx_executions_status ON workflow_executions(status);
CREATE INDEX idx_node_executions_workflow ON node_executions(workflow_execution_id);
CREATE INDEX idx_schedules_active ON schedules(is_active) WHERE is_active = true;
```

---

## 테스트 전략

### 테스트 피라미드

| 레벨 | 도구 | 커버리지 목표 | 설명 |
|------|------|--------------|------|
| Unit | pytest | 80% | 개별 함수/클래스 |
| Integration | pytest | 70% | 컴포넌트 간 연동 |
| E2E | Playwright | 주요 플로우 | 사용자 시나리오 |

### 테스트 설정

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.main import app
from app.core.config import settings


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.TEST_DATABASE_URL)
    async with AsyncSession(engine) as session:
        yield session
```

---

## 개발 환경 설정

### Docker Compose

```yaml
# docker/docker-compose.yml
services:
  frontend:
    build:
      context: ../frontend
      dockerfile: ../docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

  backend:
    build:
      context: ../backend
      dockerfile: ../docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/paste_trader
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - db
      - redis

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=paste_trader
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 환경 변수 (.env.example)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/paste_trader
REDIS_URL=redis://localhost:6379

# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
ZAI_GLM_TOKEN=...

# Security
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Scheduler
SCHEDULER_TIMEZONE=Asia/Seoul

# Logging
LOG_LEVEL=INFO
```

---

## CI/CD 설정

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: |
          cd backend
          uv sync

      - name: Run tests
        run: |
          cd backend
          uv run pytest --cov=app --cov-report=xml

      - name: Lint
        run: |
          cd backend
          uv run ruff check .

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: 9

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "pnpm"
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Install dependencies
        run: |
          cd frontend
          pnpm install

      - name: Build
        run: |
          cd frontend
          pnpm build

      - name: Test
        run: |
          cd frontend
          pnpm test
```

---

## 성능 최적화

### 캐싱 전략

| 대상 | TTL | 전략 |
|------|-----|------|
| 시장 데이터 | 1분 | Redis |
| 워크플로우 정의 | 10분 | 메모리 + Redis |
| LLM 응답 | 1시간 | Redis (동일 프롬프트) |
| 도구 결과 | 가변 | 도구별 설정 |

### 병목 지점 및 해결책

| 병목 | 해결책 |
|------|--------|
| LLM 응답 지연 | 스트리밍, 비동기 처리 |
| DB 쿼리 | 인덱스, 커넥션 풀 |
| 병렬 노드 실행 | asyncio.gather, 리소스 제한 |

---

## 보안 체크리스트

- [ ] API 키 암호화 저장 (Vault 또는 환경변수)
- [ ] 입력값 검증 (Pydantic)
- [ ] SQL Injection 방지 (SQLAlchemy ORM)
- [ ] XSS 방지 (React 기본 이스케이핑)
- [ ] CORS 설정
- [ ] Rate Limiting
- [ ] 감사 로그

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 0.1.0 | 2025-01-11 | 초기 기술 스택 정의 |
| 0.2.0 | 2025-01-11 | React Flow 상세 구현 가이드 추가, Zustand 워크플로우 스토어 추가, 입력 소스(PDF/YouTube) 파싱 코드 추가 |
