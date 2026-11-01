from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

# Strip + uppercase *before* pattern validation (StringConstraints checks the pattern first).
NormalizedUpper = BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v)

# Trimmed, non-empty strings.
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, pattern=EMAIL_PATTERN, max_length=255)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRef(ORMModel):
    id: int
    full_name: str
    email: str
