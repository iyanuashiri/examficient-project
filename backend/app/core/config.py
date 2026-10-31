from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from decouple import config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        populate_by_name=True,
        env_file=".env",
        extra="ignore",
    )

    aws_access_key_id: str = Field(
        default=config("AWS_ACCESS_KEY_ID", default=""),
            alias="AWS_ACCESS_KEY_ID",
    )
    aws_secret_access_key: str = Field(
        default=config("AWS_SECRET_ACCESS_KEY", default=""),
        alias="AWS_SECRET_ACCESS_KEY",
    )
    aws_region_name: str = Field(
        default=config("AWS_REGION_NAME", default="us-east-2"),
        alias="AWS_REGION_NAME"
    )
    meta_api_key: str = Field(default=config("META_API_KEY", default=""))

    # Use Postgres in production (set DATABASE_URL, e.g. AWS RDS) and SQLite locally.
    database_url: str = Field(
        default=config("DATABASE_URL",
                       default=f"sqlite:///{config('EXAMFICIENT_SQLITE_FILE_NAME', default='examficient.db')}",
            ),
        alias="DATABASE_URL",
    )
    # In production (ECS): the ARN of the Secrets Manager secret holding the
    # RDS credentials. The app fetches the secret at startup and builds the
    # Postgres URL from it. Empty locally.
    db_secret_arn: str = Field(default=config("DB_SECRET_ARN", default=""),
            alias="DB_SECRET_ARN",
    )
    

    # database_url: str = Field(default="sqlite:///./wintheopportunity.db", alias="DATABASE_URL")
    secret_key: str = Field(default="development-only-change-this-secret", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    @property
    def DATABASE_URL(self) -> str:
        return self.database_url
    
    @property
    def DB_SECRET_ARN(self) -> str:
        return self.db_secret_arn
    
    @property
    def AWS_ACCESS_KEY_ID(self) -> str:
        return self.aws_access_key_id
    
    @property
    def AWS_SECRET_ACCESS_KEY(self) -> str:
        return self.aws_secret_access_key
    
    @property
    def AWS_REGION_NAME(self) -> str:
        return self.aws_region_name
    
    @property
    def META_API_KEY(self) -> str:
        return self.meta_api_key


settings = Settings()




