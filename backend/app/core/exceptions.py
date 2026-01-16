"""공통 예외 클래스 정의.

TAG: [SPEC-009] [CORE] [EXCEPTIONS]
REQ: X-001, X-002 - 리소스 사용 중 체크

이 모듈은 애플리케이션 전체에서 사용하는 공통 예외 클래스를 정의합니다.
참조 무결성 체크를 위한 ResourceInUseError를 포함합니다.
"""

from __future__ import annotations

from typing import Any

# =============================================================================
# 공통 예외 기본 클래스
# =============================================================================


class AppError(Exception):
    """애플리케이션 기본 예외 클래스."""


class InvalidToolConfigError(AppError):
    """도구 설정이 유효하지 않을 때 발생하는 예외.

    도구 타입별 필수 필드가 누락된 경우 발생합니다.

    Attributes:
        tool_type: 도구 타입 (http, python, shell, mcp)
        missing_fields: 누락된 필드 이름 리스트

    Example:
        >>> raise InvalidToolConfigError(
        ...     tool_type="http",
        ...     missing_fields=["url"]
        ... )
    """

    def __init__(self, tool_type: str, missing_fields: list[str]) -> None:
        """InvalidToolConfigError를 초기화합니다.

        Args:
            tool_type: 도구 타입 (http, python, shell, mcp)
            missing_fields: 누락된 필드 이름 리스트
        """
        self.tool_type = tool_type
        self.missing_fields = missing_fields

        # 에러 메시지 생성
        fields_str = ", ".join(f"'{field}'" for field in missing_fields)
        message = (
            f"'{tool_type}' 타입의 도구 설정에 필수 필드가 누락되었습니다: "
            f"{fields_str}"
        )

        super().__init__(message)


# =============================================================================
# 리소스 참조 무결성 예외
# =============================================================================


class ResourceInUseError(AppError):
    """리소스가 사용 중일 때 발생하는 예외.

    다른 리소스에서 참조 중인 리소스를 삭제하려 할 때 발생합니다.
    어떤 리소스에서 사용되는지 정보를 포함합니다.

    Attributes:
        resource_type: 삭제하려는 리소스 타입 (예: "agent", "tool")
        resource_id: 삭제하려는 리소스 ID
        references: 이 리소스를 사용하는 참조 정보 리스트

    Example:
        >>> raise ResourceInUseError(
        ...     resource_type="agent",
        ...     resource_id="123e4567-e89b-12d3-a456-426614174000",
        ...     references=[
        ...         {"type": "workflow", "id": "...", "name": "My Workflow"},
        ...         {"type": "workflow", "id": "...", "name": "Another Workflow"},
        ...     ]
        ... )
    """

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        references: list[dict[str, Any]],
    ) -> None:
        """ResourceInUseError를 초기화합니다.

        Args:
            resource_type: 리소스 타입 (예: "agent", "tool")
            resource_id: 리소스 ID
            references: 참조 정보 리스트. 각 항목은 type, id, name을 포함해야 합니다.
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.references = references

        # 에러 메시지 생성
        ref_count = len(references)
        if ref_count == 1:
            ref_msg = f"{references[0]['type']} '{references[0].get('name', references[0]['id'])}'"
        else:
            ref_names = [
                f"{ref['type']} '{ref.get('name', ref['id'])}'" for ref in references[:3]
            ]
            if ref_count > 3:
                ref_names.append(f"외 {ref_count - 3}개")
            ref_msg = ", ".join(ref_names)

        message = (
            f"{resource_type.capitalize()} '{resource_id}'은(는) "
            f"현재 사용 중입니다. "
            f"다음 리소스에서 참조되고 있습니다: {ref_msg}"
        )

        super().__init__(message)


# =============================================================================
# 내보내기
# =============================================================================


__all__ = [
    "AppError",
    "InvalidToolConfigError",
    "ResourceInUseError",
]
