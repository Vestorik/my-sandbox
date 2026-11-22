import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from logging import Formatter, Handler, Logger, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

from concurrent_log_handler import ConcurrentRotatingFileHandler


class LogLevelEnum(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class OutputTypeEnum(Enum):
    STDOUT = "stdout"
    FILE = "file"
    THREAD = "thread"
    HTTP = "http"
    SYSLOG = "syslog"


DefaultOutput: OutputTypeEnum | None = OutputTypeEnum.THREAD


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


# ----------------------------------------------------------------------
# Dataclass-конфигурации выводов.
# Логика включения: вывод активен, если его конфиг есть и все обязательные
# параметры разрешимы (env или значения).
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StdoutOutput:
    """Вывод в консоль."""

    stream: TextIO = sys.stdout


@dataclass(frozen=True, slots=True)
class FileOutput:
    """Файл, одиночный процесс. Активен, если log_path не None."""

    log_path: Path | None = None
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass(frozen=True, slots=True)
class ThreadOutput:
    """Файл, безопасно для потоков и процессов. Активен, если log_path не None."""

    log_path: Path | None = None
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    use_gzip: bool = False  # сжимать ротированные файлы
    lock_file_directory: str | None = (
        None  # когда логи лежат в Dropbox/OneDrive и lock-файлы там не работают
    )
    chmod: int | None = None  # права на файлы (Unix)
    unicode_error_policy: str = (
        "ignore"  # что делать с символами, которые кодировка файла не берёт
    )


@dataclass(frozen=True, slots=True)
class OutputsConfig:
    stdout: StdoutOutput | None = None
    file: FileOutput | None = None
    thread: ThreadOutput | None = None

    outputs: tuple[OutputTypeEnum, ...] = field(init=False, repr=False, default=())

    def __post_init__(self) -> None:
        order = (
            (OutputTypeEnum.STDOUT, self.stdout),
            (OutputTypeEnum.FILE, self.file),
            (OutputTypeEnum.THREAD, self.thread),
        )
        object.__setattr__(
            self,
            "outputs",
            tuple(o for o, cfg in order if cfg is not None),
        )


OutputConfig = StdoutOutput | FileOutput | ThreadOutput


class LogBuilder:
    """Собирает логгер из dataclass-конфигурации выводов."""

    def __init__(
        self,
        logger_name: str,
        default_log_dir: Path = Path("logs"),
        fmt: str = (
            "%(asctime)s - %(levelname)s - %(message)s "
            "- %(filename)s - %(funcName)s - %(lineno)d"
        ),
    ) -> None:
        self.logger_name = logger_name
        self.default_log_dir = default_log_dir
        self.formatter = Formatter(fmt)
        self.default_log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _get_logger(self) -> Logger:
        return getLogger(self.logger_name)

    def _resolve_path(self, log_path: Path | None) -> Path:
        return (
            log_path
            if log_path is not None
            else (self.default_log_dir / f"{_safe_filename(self.logger_name)}.log")
        )

    # --- По одному методу на каждый тип конфига: типизация полная -----

    def _get_stdout_handler(self, config: StdoutOutput) -> Handler:
        handler: Handler = logging.StreamHandler(stream=config.stream)
        handler.setFormatter(self.formatter)
        return handler

    def _get_file_handler(self, config: FileOutput) -> Handler:
        handler = RotatingFileHandler(
            filename=str(self._resolve_path(config.log_path)),
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(self.formatter)
        return handler

    def _get_thread_handler(self, config: ThreadOutput) -> Handler:
        handler = ConcurrentRotatingFileHandler(
            filename=str(self._resolve_path(config.log_path)),
            maxBytes=config.max_bytes,
            backupCount=config.backup_count,
            encoding="utf-8",
            use_gzip=False,
            lock_file_directory=None,
            chmod=None,
            unicode_error_policy="ignore",
        )

        handler.setFormatter(self.formatter)
        return handler

    # --- Диспетчер: map enum -> (поле конфига, метод) ------------------

    def _get_log_handler(
        self,
        output: OutputTypeEnum,
        config: OutputConfig,  # union, а не object
    ) -> Handler:
        handlers: dict[OutputTypeEnum, Callable[..., Handler]] = {
            OutputTypeEnum.STDOUT: self._get_stdout_handler,
            OutputTypeEnum.FILE: self._get_file_handler,
            OutputTypeEnum.THREAD: self._get_thread_handler,
        }
        return handlers[output](config)

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def get_log_handlers(self, config: OutputsConfig) -> tuple[Handler, ...]:
        return tuple(
            self._get_log_handler(output, cfg)
            for output in config.outputs
            if (cfg := getattr(config, output.value)) is not None
        )

    def setup_logger(
        self,
        config: OutputsConfig,
        log_level: LogLevelEnum = LogLevelEnum.INFO,
    ) -> Logger:
        logger = self._get_logger()
        logger.setLevel(log_level.value)
        for handler in self.get_log_handlers(config):
            logger.addHandler(handler)
        return logger


default_config = OutputsConfig(
    stdout=StdoutOutput(),
    thread=ThreadOutput(
        log_path=Path("/tmp/parallel_app.log"),
        max_bytes=10 * 1024 * 1024,
        use_gzip=True,
        backup_count=5,
        unicode_error_policy="ignore",
    ),
)
