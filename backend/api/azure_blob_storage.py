import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME", "resumes")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

# Ensure container exists
try:
    container_client.create_container()
except Exception:
    pass


def upload_file_to_blob(file_stream, blob_name: str) -> str:
    """Upload file to Azure blob storage and return blob URL"""
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(file_stream, overwrite=True)
    return blob_client.url

def download_file_from_blob(blob_name: str) -> bytes:
    """Download file from Azure blob storage and return its content as bytes"""
    blob_client = container_client.get_blob_client(blob_name)
    if not blob_client.exists():
        return None
    downloader = blob_client.download_blob()
    return downloader.readall()


def blob_exists(blob_name: str) -> bool:
    blob_client = container_client.get_blob_client(blob_name)
    return blob_client.exists()


def delete_blob(blob_name: str):
    """Delete a blob from Azure Blob Storage."""
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.delete_blob()
