# types.py

from pydantic import BaseModel
from typing import Optional

class QueueItem(BaseModel):
    type: str
    try_start: Optional[int] = 1

    class Config:
        use_enum_values = True
