from linkfile_core import StorageType, UploadResult


def test_upload_result_accepts_core_fields() -> None:
    result = UploadResult(
        file_id="file_test",
        name="report.pdf",
        size=42,
        storage_method_id="local",
        storage_type=StorageType.LOCAL_SERVER,
        storage_key="/tmp/report.pdf",
    )

    assert result.storage_type == StorageType.LOCAL_SERVER
