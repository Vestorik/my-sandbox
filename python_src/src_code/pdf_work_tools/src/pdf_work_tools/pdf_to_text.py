"""Модуль для асинхронного извлечения текста из PDF-файлов с использованием многопоточности.

Данный модуль реализует эффективное извлечение текста из PDF без блокировки основного
асинхронного цикла. Он сочетает синхронную библиотеку `pdfplumber` с асинхронным подходом,
выполняя тяжёлую работу в пуле потоков и передавая результат через асинхронную очередь.

Основные компоненты:
- `extract_text_from_pdf`: Синхронная функция, выполняющаяся в отдельном потоке.
Открывает PDF и постранично извлекает текст, отправляя его в `asyncio.Queue`.
- `async_extract_text_from_pdf`: Асинхронный генератор, который запускает `extract_text_from_pdf`
в `ThreadPoolExecutor` и получает текст по мере готовности страниц.
- `save_text_from_pdf`: Утилита для сохранения извлечённого текста в `.txt` файл.

Особенности:
- Использование `ThreadPoolExecutor` позволяет обходить GIL и выполнять CPU-ёмкую задачу
параллельно с асинхронным приложением.
- Асинхронная очередь (`asyncio.Queue`) обеспечивает потокобезопасную передачу данных
между потоками и event loop'ом.
- Поддержка проброса исключений из потока в асинхронный контекст.
- Низкое потребление памяти за счёт потоковой обработки — текст не загружается целиком.

Используемые сторонние библиотеки:
- `pdfplumber`: Для точного извлечения текста из PDF.
- `aiofiles`: Для асинхронной записи текста в файл.
- `concurrent.futures.ThreadPoolExecutor`: Для выполнения синхронного кода вне event loop.

Типичное использование:
1. Извлечение текста из PDF: `async for text in async_extract_text_from_pdf("file.pdf")`
2. Сохранение текста: `await save_text_from_pdf("in.pdf", "out.txt")`

Важно:
- Модуль не поддерживает шифрованные PDF (обрабатываются как ошибки).
- Размер очереди можно настроить через параметр `queue_size`.
- Требуется корректная установка `pdfplumber` и зависимости `PyPDF2`.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import Self

import pdfplumber
from aiofiles import open as aiopen
from pypdfium2 import pypdfium2

logger = logging.getLogger(__name__)


class TextManager:
    def __new__(cls, *args, **kwargs) -> type[Self]:
        return cls

    @staticmethod
    def check_file(file_path: str | Path) -> bool:
        try:
            # check if the file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"File {file_path} not found")

            # check if this file is empty
            if Path(file_path).stat().st_size == 0:
                raise ValueError(f"File{file_path} is empty")

        except FileNotFoundError:
            logger.info("File %s not found", file_path)
            return False

        except ValueError:
            logger.info("File %s is empty", file_path)
            return False
        return True

    @staticmethod
    async def get_text(
        file_path: str | Path, max_text_length: int = 2621440
    ) -> AsyncGenerator[str]:
        """Асинхронно читает текст из файла построчно и возвращает порции текста заданной длины.

        Функция эффективно обрабатывает большие файлы без полной загрузки в память.
        Пустые строки пропускаются. Слишком длинные строки (длиннее `max_text_length`)
        разбиваются принудительно. Остальные строки объединяются в пакеты до достижения лимита.

        Args:
            file_path (str | Path): Путь к текстовому файлу (кодировка UTF-8).
            max_text_length (int): Максимальная длина одной порции текста в символах.
                По умолчанию 2_621_440 (~10 MiB при 4 байта на символ в UTF-8).

        Yields:
            str: Текстовая порция, готовая к дальнейшей обработке (разбиению или векторизации).

        Example:
            async for chunk in get_text("large_file.txt", max_text_length=1000):
                print(len(chunk))  # <= 1000

        Note:
            - Не включает пустые строки.
            - Гарантирует, что ни одна порция не превысит `max_text_length`.
            - Последняя порция может быть короче.
        """

        # Асинхроно читаем файл
        async with aiopen(file_path, "r", encoding="utf-8") as f:
            sample: list[str] = []
            sample_len = 0

            async for line in f:
                line = line.strip()
                if not line:  # если строка пустая пропускаем
                    continue

                len_line = len(line)

                # Одна очень длинная строка — режем её принудительно
                if len_line > max_text_length:
                    for i in range(0, len_line, max_text_length):
                        yield line[i : i + max_text_length]
                    continue

                # Собираем выборку из строк
                sample.append(line)
                sample_len += len_line

                # Если выборка больше max_text_length, возвращаем её
                if sample_len >= max_text_length:
                    text_batch: str = " ".join(sample[:-1])
                    sample = sample[-1:]  # Обновляем выборку
                    sample_len = len("".join(sample))

                    yield text_batch

            # Возвращаем остаток
            if len(sample) > 0:
                yield " ".join(sample)


class PDFManager:
    def __new__(cls, *args, **kwargs) -> type[Self]:
        return cls

    @classmethod
    def __pdf_page_pdfplamber(cls, pdf_path: str | Path):
        with pdfplumber.open(pdf_path) as pdf:
            yield from pdf.pages

    @classmethod
    def __pdf_page_pypdfium(cls, pdf_path: str | Path):
        with pypdfium2.PdfDocument(str(pdf_path)) as pdf:
            yield from pdf

    @classmethod
    def _extract_text_from_pdf(
        cls, pdf_path: str | Path, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop
    ) -> None:
        """Модуль для асинхронного извлечения текста из PDF-файлов.

        Реализует многопоточное извлечение текста с использованием библиотеки `pdfplumber`
        и передачу результата через асинхронную очередь. Позволяет эффективно обрабатывать
        PDF-документы без блокировки основного event loop.

        Основные функции:
        - `extract_text_from_pdf`: синхронная функция для выполнения в отдельном потоке.
        - `async_extract_text_from_pdf`: асинхронный генератор для постраничного чтения.
        - `save_text_from_pdf`: сохраняет извлечённый текст в файл.

        Используемые библиотеки:
        - pdfplumber
        - aiofiles
        - asyncio
        - concurrent.futures
        """

        try:
            for page in cls.__pdf_page_pypdfium(pdf_path):
                try:
                    extract_text = page.get_textpage().get_text_bounded()
                except Exception:
                    logger.warning(
                        "Не удалось извлечь страницу из %s", pdf_path, exc_info=True
                    )
                    continue

                if extract_text is None:  # if page.extract_text return None
                    continue
                else:
                    extract_text = extract_text.strip()
                    if not extract_text:  # if extract_text is empty after strip()
                        continue

                # Отправляем текст в асинхронную очередь из другого потока
                asyncio.run_coroutine_threadsafe(
                    queue.put(extract_text + "\n"), loop
                ).result()

            # Сообщаем о завершении обработки
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        except Exception as e:
            logger.warning("Ошибка при извлечении текста из PDF %s", e)
            # Помещаем исключение в очередь для обработки в основном цикле
            loop.call_soon_threadsafe(queue.put_nowait, e)
            loop.call_soon_threadsafe(queue.put_nowait, None)

    @classmethod
    async def async_extract_text_from_pdf(
        cls, pdf_path: str | Path, queue_size: int = 10
    ) -> AsyncGenerator[str | None]:
        """Асинхронно извлекает текст из PDF-файла постранично с использованием пула потоков.

        Данная функция запускает синхронную функцию извлечения текста `extract_from_pdf`
        в отдельном потоке через `ThreadPoolExecutor`. Извлечённый текст передаётся через
        асинхронную очередь и предоставляется постранично с помощью генератора. Функция
        завершается, когда получает сигнал `None` из очереди, что означает окончание обработки.
        Любые исключения, возникшие в потоке, пробрасываются в вызывающий код.

        Аргументы:
            pdf_path (str | Path): Путь к PDF-файлу, который необходимо обработать.
            queue_size (int): Максимальный размер внутренней очереди для буферизации
                            извлекаемых страниц. По умолчанию — 10. Увеличение значения
                            может повысить производительность при работе с большими файлами,
                            но потребует больше памяти.

        Возвращает:
            AsyncGenerator[str, None]: Асинхронный генератор, выдающий строки текста
                                    по мере извлечения каждой страницы. Каждая строка
                                    соответствует одной странице PDF (с обрезанными
                                    пробелами и добавленным переводом строки).

        Исключения:
            Любой объект исключения, помещённый в очередь из потока, будет проброшен
            наверх в вызывающий асинхронный контекст.

        Примечания:
            - Функция корректно освобождает ресурсы пула потоков в блоке `finally`.
            - Используется `asyncio.Queue` для межпотокового взаимодействия.
            - Работает совместно с функцией `extract_from_pdf`, которая выполняется в пуле потоков.
            - Не рекомендуется использовать с очень большими PDF без учёта ограничений памяти.

        Пример использования:
            >>> async for page_text in extract_text_from_pdf("document.pdf"):
            ...     print(page_text)
            ...
            Содержимое первой страницы...
            Содержимое второй страницы...

            >>> try:
            ...     async for text in extract_text_from_pdf("broken.pdf"):
            ...         await process(text)
            ... except Exception as e:
            ...     print(f"Ошибка при обработке PDF: {e}")
        """
        queue = asyncio.Queue(maxsize=queue_size)
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor()

        pdf_func = partial(
            cls._extract_text_from_pdf,
            pdf_path,
            queue,
            loop,
        )

        try:
            # Запускаем извлечение текста в отдельном потоке
            loop.run_in_executor(executor, pdf_func)

            while True:
                item = await queue.get()

                if item is None:
                    break  # Признак завершения
                if isinstance(item, Exception):
                    raise item  # Проброс исключения из потока
                yield item  # Выдача текста страницы

        except Exception as e:
            logger.warning("Ошибка при асинхронной работе %s", e)
            raise

        finally:
            executor.shutdown(wait=True)

    @classmethod
    async def save_text_from_pdf(
        cls, from_pdf_path: str | Path, save_text_path: str | Path
    ):
        """Асинхронно извлекает текст из PDF-файла и сохраняет его в текстовый файл.

        Функция использует асинхронный генератор `async_extract_text_from_pdf` для постраничного
        или последовательного чтения текста из PDF. Каждая порция извлечённого текста записывается
        в указанный файл по мере поступления. Это позволяет эффективно обрабатывать большие PDF,
        не загружая весь текст в память.

        В случае успешного завершения операции в лог записывается сообщение об успехе.
        При возникновении ошибки (например, проблемы с доступом к файлу, повреждённый PDF и т.п.)
        ошибка логируется на уровне WARNING, после чего исключение пробрасывается выше для обработки.

        Args:
            from_pdf_path (str | Path): Путь к входному PDF-файлу, из которого необходимо извлечь текст.
            save_text_path (str | Path): Путь к выходному текстовому файлу, в который будет сохранён результат.
                Если файл существует, он будет перезаписан.

        Raises:
            Exception: Любое исключение, возникшее при чтении PDF или записи текста,
                например: FileNotFoundError, PermissionError, OSError, а также ошибки парсинга PDF.
                Исключение логируется и повторно поднимается.

        Example:
            await save_text_from_pdf("document.pdf", "extracted_text.txt")

        Note:
            - Кодировка записи — UTF-8. Убедитесь, что извлечённый текст корректно кодируется.
            - Для работы требуется установленная библиотека `aiofiles`, а также средство извлечения
            текста из PDF `pdfplumber`.

        Logging:
            - info: При успешном сохранении текста.
            - warning: При любой ошибке в процессе извлечения или записи.
        """
        try:
            async with aiopen(save_text_path, "w", encoding="utf-8") as f:
                async for text in cls.async_extract_text_from_pdf(from_pdf_path):
                    if text is None:
                        continue

                    else:
                        await f.write(text)

                logger.info("Текст успешно сохранен в %s", save_text_path)
        except Exception as e:
            logger.warning("Ошибка при сохранении текста в файл %s", e)
            raise
