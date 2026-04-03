from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PresignedUploadRequest:
    content_type: str
    original_filename: str
    max_size_bytes: int


@dataclass(slots=True)
class PresignedUploadResponse:
    bucket_name: str
    storage_key: str
    upload_url: str


class ObjectStorageService(Protocol):
    async def create_upload(self, payload: PresignedUploadRequest) -> PresignedUploadResponse:
        ...
