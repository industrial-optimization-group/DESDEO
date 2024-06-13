"""Tests for configuration."""
from desdeo.api import AuthConfig, DBConfig

def test_default_config():
    """Test configs after load_config()."""

    assert AuthConfig.authjwt_secret_key is not None
    assert AuthConfig.authjwt_algorithm is not None
    assert AuthConfig.authjwt_access_token_expires is not None
    assert AuthConfig.authjwt_refresh_token_expires is not None

    assert DBConfig.db_host is not None
    assert DBConfig.db_port is not None
    assert DBConfig.db_database is not None
    assert DBConfig.db_username is not None
    assert DBConfig.db_password is not None
    assert DBConfig.db_pool_size is not None
    assert DBConfig.db_max_overflow is not None
    assert DBConfig.db_pool is not None