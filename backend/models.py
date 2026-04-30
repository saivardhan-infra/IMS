from pydantic import BaseModel
from datetime import datetime

class Signal(BaseModel):
    component_id: str
    message: str
    timestamp: datetime

class RCA(BaseModel):
    cause: str
    fix: str
