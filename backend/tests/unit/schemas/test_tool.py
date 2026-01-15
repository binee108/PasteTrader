"""
Tool 스키마에 대한 단위 테스트

TDD RED 단계: 모든 테스트가 처음에는 실패해야 합니다.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

# 테스트 대상 모듈 (아직 구현되지 않음)
from app.schemas.tool import (
    ToolCreate,
    ToolDetailResponse,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)


class TestToolCreate:
    """ToolCreate 스키마 테스트"""

    def test_valid_tool_create(self):
        """유효한 ToolCreate 생성 성공"""
        tool_data = {
            "name": "test_tool",
            "description": "Test tool description",
            "parameters": {"type": "object", "properties": {}},
            "implementation_path": "tools/test_tool.py",
        }
        tool = ToolCreate(**tool_data)

        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.parameters == {"type": "object", "properties": {}}
        assert tool.implementation_path == "tools/test_tool.py"

    def test_name_min_length_validation(self):
        """name 필드 최소 길이 검증 (1글자 이상)"""
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(name="", parameters={})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_name_max_length_validation(self):
        """name 필드 최대 길이 검증 (255글자 이하)"""
        long_name = "a" * 256
        with pytest.raises(ValidationError) as exc_info:
            ToolCreate(name=long_name, parameters={})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_optional_fields_can_be_none(self):
        """선택적 필드는 None이 가능"""
        tool = ToolCreate(name="test_tool", parameters={})

        assert tool.name == "test_tool"
        assert tool.description is None
        assert tool.implementation_path is None

    def test_parameters_must_be_dict(self):
        """parameters 필드는 dict 타입이어야 함"""
        with pytest.raises(ValidationError):
            ToolCreate(name="test_tool", parameters="invalid")

    def test_parameters_accepts_json_schema(self):
        """parameters는 JSON Schema 구조를 허용"""
        json_schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "timeout": {"type": "integer", "minimum": 1},
            },
            "required": ["url"],
        }
        tool = ToolCreate(name="http_tool", parameters=json_schema)

        assert tool.parameters == json_schema


class TestToolUpdate:
    """ToolUpdate 스키마 테스트"""

    def test_all_fields_optional(self):
        """모든 필드는 선택적 (빈 데이터로 생성 가능)"""
        tool_update = ToolUpdate()
        assert tool_update.description is None
        assert tool_update.parameters is None
        assert tool_update.implementation_path is None
        assert tool_update.is_active is None

    def test_partial_update_description(self):
        """description만 업데이트"""
        tool_update = ToolUpdate(description="Updated description")
        assert tool_update.description == "Updated description"
        assert tool_update.parameters is None
        assert tool_update.is_active is None

    def test_partial_update_parameters(self):
        """parameters만 업데이트"""
        new_params = {"type": "object", "properties": {"new_field": {"type": "string"}}}
        tool_update = ToolUpdate(parameters=new_params)
        assert tool_update.parameters == new_params

    def test_partial_update_is_active(self):
        """is_active만 업데이트"""
        tool_update = ToolUpdate(is_active=False)
        assert tool_update.is_active is False

    def test_update_all_fields(self):
        """모든 필드 업데이트"""
        tool_update = ToolUpdate(
            description="Updated",
            parameters={"type": "object"},
            implementation_path="new_path.py",
            is_active=True,
        )
        assert tool_update.description == "Updated"
        assert tool_update.parameters == {"type": "object"}
        assert tool_update.implementation_path == "new_path.py"
        assert tool_update.is_active is True


class TestToolResponse:
    """ToolResponse 스키마 테스트"""

    def test_from_orm_object(self):
        """ORM 객체로부터 ToolResponse 생성 (from_attributes)"""

        # ORM 객체를 시뮬레이션하는 더미 클래스
        class DummyTool:
            id = uuid4()
            name = "test_tool"
            description = "Test description"
            parameters = {"type": "object"}
            implementation_path = "tools/test.py"
            is_active = True
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()

        dummy = DummyTool()
        response = ToolResponse.model_validate(dummy)

        assert isinstance(response.id, UUID)
        assert response.name == "test_tool"
        assert response.description == "Test description"
        assert response.parameters == {"type": "object"}
        assert response.implementation_path == "tools/test.py"
        assert response.is_active is True
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)

    def test_response_with_none_updated_at(self):
        """updated_at이 None인 경우"""

        class DummyTool:
            id = uuid4()
            name = "test_tool"
            description = None
            parameters = {}
            implementation_path = None
            is_active = True
            created_at = datetime.utcnow()
            updated_at = None

        dummy = DummyTool()
        response = ToolResponse.model_validate(dummy)

        assert response.updated_at is None

    def test_response_field_types(self):
        """모든 필드 타입 검증"""
        tool_id = uuid4()
        now = datetime.utcnow()

        class DummyTool:
            id = tool_id
            name = "test"
            description = "desc"
            parameters = {}
            implementation_path = "path"
            is_active = True
            created_at = now
            updated_at = now

        dummy = DummyTool()
        response = ToolResponse.model_validate(dummy)

        assert isinstance(response.id, UUID)
        assert isinstance(response.name, str)
        assert isinstance(response.parameters, dict)
        assert isinstance(response.is_active, bool)
        assert isinstance(response.created_at, datetime)


class TestToolDetailResponse:
    """ToolDetailResponse 스키마 테스트"""

    def test_inherits_from_tool_response(self):
        """ToolResponse 상속 확인"""
        agent_id = uuid4()
        workflow_id = uuid4()

        class DummyTool:
            id = uuid4()
            name = "test_tool"
            description = "desc"
            parameters = {}
            implementation_path = "path"
            is_active = True
            created_at = datetime.utcnow()
            updated_at = None
            used_by_agents = [agent_id]
            used_in_workflows = [workflow_id]

        dummy = DummyTool()
        detail_response = ToolDetailResponse.model_validate(dummy)

        # ToolResponse 필드
        assert detail_response.name == "test_tool"
        assert detail_response.is_active is True

        # ToolDetailResponse 추가 필드
        assert isinstance(detail_response.used_by_agents, list)
        assert isinstance(detail_response.used_in_workflows, list)
        assert agent_id in detail_response.used_by_agents
        assert workflow_id in detail_response.used_in_workflows

    def test_default_empty_lists(self):
        """used_by_agents와 used_in_workflows 기본값은 빈 리스트"""

        class DummyTool:
            id = uuid4()
            name = "test"
            description = None
            parameters = {}
            implementation_path = None
            is_active = True
            created_at = datetime.utcnow()
            updated_at = None
            # used_by_agents와 used_in_workflows 속성 없음

        dummy = DummyTool()
        detail_response = ToolDetailResponse.model_validate(dummy)

        assert detail_response.used_by_agents == []
        assert detail_response.used_in_workflows == []

    def test_multiple_agents_and_workflows(self):
        """여러 에이전트와 워크플로우 연결"""
        agent_ids = [uuid4() for _ in range(3)]
        workflow_ids = [uuid4() for _ in range(2)]

        class DummyTool:
            id = uuid4()
            name = "multi_use_tool"
            description = None
            parameters = {}
            implementation_path = None
            is_active = True
            created_at = datetime.utcnow()
            updated_at = None
            used_by_agents = agent_ids
            used_in_workflows = workflow_ids

        dummy = DummyTool()
        detail_response = ToolDetailResponse.model_validate(dummy)

        assert len(detail_response.used_by_agents) == 3
        assert len(detail_response.used_in_workflows) == 2
        for agent_id in agent_ids:
            assert agent_id in detail_response.used_by_agents
        for workflow_id in workflow_ids:
            assert workflow_id in detail_response.used_in_workflows


class TestToolTestRequest:
    """ToolTestRequest 스키마 테스트"""

    def test_valid_test_request(self):
        """유효한 ToolTestRequest 생성"""
        request = ToolTestRequest(params={"url": "https://example.com"}, timeout=30)

        assert request.params == {"url": "https://example.com"}
        assert request.timeout == 30

    def test_default_timeout_value(self):
        """timeout 기본값은 30"""
        request = ToolTestRequest(params={})

        assert request.timeout == 30

    def test_timeout_minimum_validation(self):
        """timeout 최소값 검증 (>= 1)"""
        with pytest.raises(ValidationError) as exc_info:
            ToolTestRequest(params={}, timeout=0)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timeout",) for e in errors)

    def test_timeout_maximum_validation(self):
        """timeout 최대값 검증 (<= 120)"""
        with pytest.raises(ValidationError) as exc_info:
            ToolTestRequest(params={}, timeout=121)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timeout",) for e in errors)

    def test_timeout_boundary_values(self):
        """timeout 경계값 테스트 (1과 120)"""
        request_min = ToolTestRequest(params={}, timeout=1)
        assert request_min.timeout == 1

        request_max = ToolTestRequest(params={}, timeout=120)
        assert request_max.timeout == 120

    def test_params_accepts_any_dict(self):
        """params는 모든 dict 구조 허용"""
        various_params = [
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"array": [1, 2, 3]},
            {"mixed": {"str": "text", "num": 123, "bool": True, "arr": []}},
        ]

        for params in various_params:
            request = ToolTestRequest(params=params)
            assert request.params == params


class TestToolTestResponse:
    """ToolTestResponse 스키마 테스트"""

    def test_successful_test_response(self):
        """성공적인 테스트 응답"""
        response = ToolTestResponse(
            success=True,
            result={"status": "ok", "data": "test result"},
            error=None,
            execution_time_ms=150,
            logs=["Starting test...", "Test completed"],
        )

        assert response.success is True
        assert response.result == {"status": "ok", "data": "test result"}
        assert response.error is None
        assert response.execution_time_ms == 150
        assert response.logs == ["Starting test...", "Test completed"]

    def test_failed_test_response(self):
        """실패한 테스트 응답"""
        response = ToolTestResponse(
            success=False,
            result=None,
            error="Connection timeout",
            execution_time_ms=5000,
            logs=["Connecting...", "Timeout after 5s"],
        )

        assert response.success is False
        assert response.result is None
        assert response.error == "Connection timeout"
        assert response.execution_time_ms == 5000
        assert len(response.logs) == 2

    def test_default_empty_logs(self):
        """logs 기본값은 빈 리스트"""
        response = ToolTestResponse(
            success=True, result={"data": "value"}, execution_time_ms=100
        )

        assert response.logs == []

    def test_execution_time_ms_type(self):
        """execution_time_ms는 정수형"""
        response = ToolTestResponse(success=True, result={}, execution_time_ms=123)

        assert isinstance(response.execution_time_ms, int)
        assert response.execution_time_ms == 123

    def test_result_and_error_mutual_exclusivity_not_enforced(self):
        """result와 error는 상호 배타적이지 않음 (둘 다 존재 가능)"""
        # 스키마에서는 둘 다 허용하므로 테스트
        response = ToolTestResponse(
            success=True,
            result={"partial": "result"},
            error="Warning message",
            execution_time_ms=100,
        )

        assert response.result is not None
        assert response.error is not None

    def test_optional_fields_can_be_omitted(self):
        """선택적 필드 생략 가능"""
        response = ToolTestResponse(success=True, result={}, execution_time_ms=50)

        assert response.error is None
        assert response.logs == []

    def test_complex_result_structure(self):
        """복잡한 result 구조 지원"""
        complex_result = {
            "nested": {"data": {"deep": "value"}},
            "array": [1, 2, {"key": "val"}],
            "mixed": ["text", 123, True, None],
        }

        response = ToolTestResponse(
            success=True, result=complex_result, execution_time_ms=200
        )

        assert response.result == complex_result
