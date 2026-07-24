from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # База данных
    db_host: str = "localhost"
    db_port: int = 5434
    db_name: str = "repoteka"
    db_user: str = "postgres"
    db_password: str = "root"
    
    # Repoteka API
    repoteka_url: str = "https://rdb.altlinux.org/repoteka"
    repoteka_timeout: int = 30
    
    # API сервер
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    
    # Загрузчик
    load_batch_size: int = 1000
    load_interval_hours: int = 24
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"