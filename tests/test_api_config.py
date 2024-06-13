"""Tests for configuration."""
from desdeo.api.auth_config import AuthConfig
from pydantic import BaseModel

def test_config_before_load():
    """Test configs before load_config()."""

    assert AuthConfig._secret_key is None
    assert AuthConfig._algorithm is None
    assert AuthConfig._access_token_expires is None
    assert AuthConfig._refresh_token_expires is None

def test_default_config_after_load():
    """Test configs after load_config()."""

    AuthConfig.load_config()

    assert AuthConfig._secret_key is not None
    assert AuthConfig._algorithm is not None
    assert AuthConfig._access_token_expires is not None
    assert AuthConfig._refresh_token_expires is not None

def test_overwrite_config():
    """Test configs with overwritten values."""

    class Settings(BaseModel):
        authjwt_secret_key: str = "testing"
        authjwt_algorithm: str = "testing"
        authjwt_access_token_expires: int = 9999
        authjwt_refresh_token_expires: int = 99999

    # callback to get your configuration
    @AuthConfig.load_config
    def get_settings():
        return Settings()

    assert AuthConfig._secret_key == "testing"
    assert AuthConfig._algorithm == "testing"
    assert AuthConfig._access_token_expires == 9999
    assert AuthConfig._refresh_token_expires == 99999