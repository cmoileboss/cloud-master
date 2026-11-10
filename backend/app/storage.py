import logging
from pathlib import Path
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger("ffk.storage")


class BlobStorage:
    def __init__(self, account_url: str, container_name: str):
        self.client = BlobServiceClient(
            account_url=account_url,
            credential=DefaultAzureCredential()
        )
        self.container = self.client.get_container_client(container_name)

    def put(self, key: str, content: bytes, content_type: str = "application/pdf") -> None:
        self.container.upload_blob(
            name=key,
            data=content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
        logger.info("storage_put key=%s size=%d", key, len(content))

    def get(self, key: str) -> bytes:
        blob = self.container.download_blob(key)
        content = blob.readall()
        logger.debug("storage_get key=%s size=%d", key, len(content))
        return content
