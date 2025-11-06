from typing import Callable, List, Dict, Awaitable
from pathlib import Path
from .file import writeYMLFile, readYMLFile, create_file
from .schemas import ConfigItem, ConfigItemType
import asyncio


# ==============================
# Вспомогательные функции
# ==============================

def filter_delete(key: str):
    def _filter_delete(data: ConfigItem):
        return key != data.key
    return _filter_delete


def delete_value(item: ConfigItem):
    """Маскирует значение пароля (длина вместо содержимого)."""
    return ConfigItem(
        key=item.key,
        tag=item.tag,
        type=item.type,
        value=str(len(item.value))
    )


def itemConfig(tag: str, key: str, value: str = '', type: ConfigItemType = ConfigItemType.TEXT):
    """Упрощённый конструктор ConfigItem."""
    return ConfigItem(key=key, value=value, tag=tag, type=type)


# ==============================
# Основной класс Config
# ==============================

class Config:
    def __init__(self, dir: str, file_name: str = 'service_config'):
        self.callback: Dict[str, Callable[[], Awaitable[None]]] = {}
        self.config: List[ConfigItem] = []
        self.file: Path = create_file(dir, file_name)

    def __repr__(self):
        return f"<Config file='{self.file}' items={len(self.config)}>"

    # ------------------------------
    # Внутренние методы
    # ------------------------------

    def __parse_conf(self) -> List[Dict]:
        """Преобразует список ConfigItem в сериализуемый формат."""
        return [x.model_dump() for x in self.config]

    # ------------------------------
    # Основная логика
    # ------------------------------

    def get(self, key: str) -> ConfigItem | None:
        for item in self.config:
            if key == item.key:
                return item
        return None

    def register_config(self, data: ConfigItem, callback: Callable[[], Awaitable[None]] | None = None):
        """Регистрирует новый элемент конфигурации и при необходимости callback."""
        if self.get(data.key):
            return
        self.config.append(data)
        if callback:
            self.callback[data.key] = callback

    async def set(self, key: str, value: str):
        """Обновляет значение и вызывает callback (если есть)."""
        for item in self.config:
            if key == item.key:
                item.value = value
                if key in self.callback:
                    await self.callback[key]()
                break

    async def restart(self):
        """Вызывает все callbacks (например, при перезапуске)."""
        await asyncio.gather(*(cb() for cb in self.callback.values()))

    async def set_and_save(self, key: str, value: str):
        await self.set(key, value)
        self.save()

    async def set_dict(self, data: Dict[str, str]):
        """Устанавливает сразу несколько параметров (параллельно)."""
        await asyncio.gather(*(self.set(k, v) for k, v in data.items()))

    def delete(self, key: str):
        """Удаляет параметр и его callback."""
        self.config = list(filter(filter_delete(key), self.config))
        self.callback.pop(key, None)

    def get_all_data(self) -> List[ConfigItem]:
        """Возвращает все элементы (пароли маскируются)."""
        return [
            delete_value(item) if item.type == ConfigItemType.PASSWORD else ConfigItem(**item.dict())
            for item in self.config
        ]

    def get_all_raw(self) -> List[ConfigItem]:
        """Возвращает все элементы как есть (включая пароли)."""
        return self.config

    # ------------------------------
    # Работа с файлами
    # ------------------------------

    def save(self):
        """Безопасно сохраняет конфигурацию в YAML."""
        tmp_file = self.file.with_suffix('.tmp')
        writeYMLFile(tmp_file, self.__parse_conf())
        tmp_file.replace(self.file)

    async def load(self, trigger_callbacks: bool = True):
        """Загружает конфигурацию из файла.
        Если trigger_callbacks=True, вызывает колбэки.
        """
        data = readYMLFile(self.file)
        if not data:
            return

        for item in data:
            item_data = ConfigItem(**item)
            cfg_item = self.get(item_data.key)
            if not cfg_item:
                continue

            if trigger_callbacks:
                await self.set(item_data.key, item_data.value)
            else:
                cfg_item.value = item_data.value
