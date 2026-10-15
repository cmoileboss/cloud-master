from pathlib import Path


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

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):  # refuse « ../../fichier »
            raise ValueError(f"Clé de stockage invalide : {key}")
        return path
