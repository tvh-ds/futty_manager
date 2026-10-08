import json
from pathlib import Path


def transfer_volume(local: Path, volume: str, download: bool):
    from databricks.sdk import WorkspaceClient
    if not volume.startswith("/Volumes/") or ".." in volume.split("/"):
        raise ValueError("Use an absolute managed Unity Catalog volume path")
    workspace = WorkspaceClient()
    if download:
        response = workspace.files.download(volume)
        local.parent.mkdir(parents=True, exist_ok=True)
        with local.open("wb") as destination:
            for chunk in iter(lambda: response.contents.read(1024 * 1024), b""):
                destination.write(chunk)
    else:
        with local.open("rb") as source:
            workspace.files.upload(volume, source, overwrite=False)


def upload_blob(local: Path, account: str, container: str, name: str):
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    if not account.isalnum():
        raise ValueError("Invalid storage account")
    client = BlobServiceClient(f"https://{account}.blob.core.windows.net", credential=DefaultAzureCredential())
    with local.open("rb") as stream:
        client.get_blob_client(container, name).upload_blob(stream, overwrite=False)


def integration_probe(volume: str):
    from databricks.sdk import WorkspaceClient
    workspace = WorkspaceClient()
    results = {"identity": workspace.current_user.me().user_name, "volume": volume,
               "files": [item.path for item in workspace.files.list_directory_contents(volume)]}
    Path("artifacts/integration").mkdir(parents=True, exist_ok=True)
    Path("artifacts/integration/databricks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results
