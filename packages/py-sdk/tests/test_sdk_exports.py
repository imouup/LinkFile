from linkfile import LinkFileClient, LocalLinkFileClient


def test_sdk_exports_clients() -> None:
    assert LinkFileClient("https://example.com").base_url == "https://example.com"
    assert LocalLinkFileClient.from_config().config_file.name == "config.json"
