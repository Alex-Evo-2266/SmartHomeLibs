import pytest
import asyncio
from pathlib import Path
from config_lib.src.config import Config, ConfigItem, ConfigItemType

@pytest.mark.asyncio
async def test_register_and_get_config(tmp_path: Path):
    cfg = Config(str(tmp_path))
    
    item = ConfigItem(key="test", value="123", type=ConfigItemType.TEXT)
    cfg.register_config(item)
    
    # Проверяем регистрацию
    fetched = cfg.get("test")
    assert fetched is not None
    assert fetched.value == "123"
    
    # Дубликаты не регистрируются
    cfg.register_config(item)
    assert len(cfg.get_all_raw()) == 1


@pytest.mark.asyncio
async def test_set_and_callback(tmp_path: Path):
    cfg = Config(str(tmp_path))
    called = False

    async def callback():
        nonlocal called
        called = True

    item = ConfigItem(key="key1", value="val1", type=ConfigItemType.TEXT)
    cfg.register_config(item, callback)

    await cfg.set("key1", "new_val")
    assert cfg.get("key1").value == "new_val"
    assert called is True


@pytest.mark.asyncio
async def test_set_dict(tmp_path: Path):
    cfg = Config(str(tmp_path))
    keys = ["a", "b", "c"]
    for k in keys:
        cfg.register_config(ConfigItem(key=k, value="0", type=ConfigItemType.NUMBER))

    data = { "a": "1", "b": "2", "c": "3" }
    await cfg.set_dict(data)

    for k, v in data.items():
        assert cfg.get(k).value == v


@pytest.mark.asyncio
async def test_set_and_save_load(tmp_path: Path):
    cfg = Config(str(tmp_path))
    cfg.register_config(ConfigItem(key="pass", value="secret", type=ConfigItemType.PASSWORD))
    
    await cfg.set_and_save("pass", "new_secret")
    # После сохранения файл должен существовать
    assert cfg.file.exists()

    # Создаем новый объект и загружаем
    cfg2 = Config(str(tmp_path))
    cfg2.register_config(ConfigItem(key="pass", value="", type=ConfigItemType.PASSWORD))
    await cfg2.load()
    assert cfg2.get("pass").value == "new_secret"


def test_delete_and_get_all_data(tmp_path: Path):
    cfg = Config(str(tmp_path))
    cfg.register_config(ConfigItem(key="text", value="hello", type=ConfigItemType.TEXT))
    cfg.register_config(ConfigItem(key="pwd", value="12345", type=ConfigItemType.PASSWORD))

    cfg.delete("text")
    assert cfg.get("text") is None

    data = cfg.get_all_data()
    # Пароль маскируется
    pwd_item = next(i for i in data if i.key == "pwd")
    assert pwd_item.value == "5"


@pytest.mark.asyncio
async def test_restart_callbacks(tmp_path: Path):
    cfg = Config(str(tmp_path))
    call_order = []

    async def cb1():
        call_order.append("cb1")
    async def cb2():
        call_order.append("cb2")

    cfg.register_config(ConfigItem(key="a", value="1", type=ConfigItemType.TEXT), cb1)
    cfg.register_config(ConfigItem(key="b", value="2", type=ConfigItemType.TEXT), cb2)

    await cfg.restart()
    assert set(call_order) == {"cb1", "cb2"}
