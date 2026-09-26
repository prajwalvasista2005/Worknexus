from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CourseCreate(BaseModel):
    course_id: str = Field(..., max_length=50, description="Unique course identifier code e.g. COURSE-CS101")
    name: str = Field(..., max_length=255, description="Course name / title")
    description: str | None = Field(default=None, description="Detailed syllabus or course overview")
    department: str = Field(..., max_length=100, description="Department or vocational sector")
    semester: str | None = Field(default=None, max_length=50, description="Semester or duration term")
    is_active: bool = Field(default=True, description="Active status flag")


class CourseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    department: str | None = None
    semester: str | None = None
    is_active: bool | None = None


class CourseResponse(BaseModel):
    id: int
    course_id: str
    name: str
    description: str | None = None
    department: str
    semester: str | None = None
    is_active: bool
    created_at: datetime
    title: str | None = None
    code: str | None = None
    provider: str | None = None
    duration_weeks: int = 12

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context):
        if self.title is None:
            self.title = self.name
        if self.code is None:
            self.code = self.course_id
        if self.provider is None:
            self.provider = self.department
