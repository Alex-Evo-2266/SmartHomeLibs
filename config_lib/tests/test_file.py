import yaml
from pathlib import Path
from config_lib.src.file import writeYMLFile, readYMLFile, create_file


def test_create_file_creates_dir_and_file(tmp_path: Path):
    # Создание пути
    test_dir = tmp_path / "nested" / "config"
    file_path = create_file(str(test_dir), "settings")

    # Проверка — каталог создан
    assert test_dir.exists() and test_dir.is_dir()
    # Проверка — файл создан
    assert file_path.exists() and file_path.is_file()
    # Проверка — имя файла корректное
    assert file_path.name == "settings.yml"


def test_write_and_read_yml_file(tmp_path: Path):
    path = tmp_path / "config.yml"
    data = {"key": "value", "nested": {"a": 1, "b": 2}}

    # Запись данных
    writeYMLFile(path, data)

    # Проверяем, что файл существует
    assert path.exists()

    # Чтение обратно
    result = readYMLFile(path)

    assert isinstance(result, dict)
    assert result["key"] == "value"
    assert result["nested"]["a"] == 1


def test_read_yml_file_returns_none_if_not_exists(tmp_path: Path):
    path = tmp_path / "no_file.yml"
    result = readYMLFile(path)
    assert result is None


def test_read_yml_file_returns_none_if_empty(tmp_path: Path):
    path = tmp_path / "empty.yml"
    path.touch()  # создаём пустой файл
    result = readYMLFile(path)
    assert result is None


def test_write_yml_file_preserves_unicode(tmp_path: Path):
    path = tmp_path / "unicode.yml"
    data = {"greeting": "Привет 🌍"}

    writeYMLFile(path, data)
    loaded = readYMLFile(path)

    assert loaded == data
    # Убедимся, что содержимое файла в UTF-8
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Привет" in content
