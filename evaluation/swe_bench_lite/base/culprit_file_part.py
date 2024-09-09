from ghostos.core.moss.decorators import cls_source_code
from pydantic import BaseModel, Field


@cls_source_code()
class CulpritFilePart(BaseModel):
    file_path: str = Field(..., description="The path of the culprit file")
    culprit_reason: str = Field(..., description="The reason why the part is the culprit")
    culprit_line_start: int = Field(..., description="The start line of the culprit")
    culprit_line_end: int = Field(..., description="The end line of the culprit")
    confidence_percentage: int = Field(..., description="The confidence percentage of the culprit")
