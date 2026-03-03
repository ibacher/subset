from pydantic_settings import BaseSettings, SettingsConfigDict


class SupersetConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="SUPERSET_"
    )

    base_url: str | None = None
    username: str | None = None
    password: str | None = None
    api_token: str | None = None

    @property
    def uses_password_auth(self) -> bool:
        return bool(self.username and self.password)

    @property
    def uses_token_auth(self) -> bool:
        return bool(self.api_token)

    def validate_for_connection(self) -> None:
        if not self.base_url:
            raise ValueError("SUPERSET_BASE_URL is required")
        if not self.uses_password_auth and not self.uses_token_auth:
            raise ValueError("Either username/password or api_token is required")
