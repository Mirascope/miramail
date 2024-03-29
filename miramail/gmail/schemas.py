from pydantic import BaseModel

class AttachmentMetadata(BaseModel):
    raw_data: bytes
    file_name: str
    content_type: str = "application/octet-stream"