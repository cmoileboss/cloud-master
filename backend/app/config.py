from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Paramètres lus dans les variables d'environnement, puis dans le fichier `.env` à la racine du projet.

    Chaque attribut correspond à une variable en majuscules : `database_url` ↔ `DATABASE_URL`.
    """

    model_config = SettingsConfigDict(env_file=BACKEND_DIR.parent / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ffk:ffk-local-only@127.0.0.1:5433/ffk"
    data_dir: Path = BACKEND_DIR / "data"
    cors_origins: str = "http://localhost:5173"

    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")

    @property
    def cors_origin_list(self) -> list[str]:
        """Origines séparées par des virgules ; espaces et slash final tolérés."""
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]
