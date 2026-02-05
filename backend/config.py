from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    dedup_window: float = 2.0
    sensor_timeout: float = 5.0
    server_host: str = "0.0.0.0"
    server_port: int = 8080
    data_dir: Path = Path(__file__).parent / "data"

    @property
    def product_map_file(self) -> Path:
        return self.data_dir / "product_map.csv"

    @property
    def gateways_file(self) -> Path:
        return self.data_dir / "gateways.json"


settings = Settings()
