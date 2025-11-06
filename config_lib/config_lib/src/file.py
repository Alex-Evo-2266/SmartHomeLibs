from pathlib import Path
import yaml

def writeYMLFile(path: Path, data: object) -> None:
    """Записывает данные в YAML-файл (читаемый формат)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def readYMLFile(path: Path):
    """Читает YAML-файл и возвращает объект Python (или None, если пуст)."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def create_file(dir: str, file_name: str) -> Path:
    """Создаёт каталог (если не существует) и возвращает путь к YAML-файлу."""
    path = Path(dir)
    path.mkdir(parents=True, exist_ok=True)
    file_path = path / f"{file_name}.yml"
    if not file_path.exists():
        file_path.touch()
    return file_path
