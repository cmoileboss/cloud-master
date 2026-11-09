import logging
from pathlib import Path

logger = logging.getLogger("ffk.storage")


class LocalStorage:
    """Stockage des PDF dans un dossier local.

    Pour utiliser un autre stockage, écrire une classe avec les mêmes méthodes `put` et `get`,
    puis l'instancier dans `create_app` (app/main.py). Le reste de l'application ne change pas.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    def put(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.info("storage_put key=%s size=%d", key, len(content))

    def get(self, key: str) -> bytes:
        content = self._path(key).read_bytes()
        logger.debug("storage_get key=%s size=%d", key, len(content))
        return content

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):  # refuse « ../../fichier »
            logger.warning("storage_invalid_key key=%r", key)
            raise ValueError(f"Clé de stockage invalide : {key}")
        return path
