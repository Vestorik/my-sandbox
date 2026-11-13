import sys
import time

class TimeTracer:
    """Таймер, привязанный к фрейму функции-владельца.

    При создании запоминает фрейм вызывающей функции и время старта.
    Каждый вызов экземпляра (без аргументов) возвращает время,
    прошедшее с момента старта.
    """
    def __time_now(self, current_time: float | None = None) -> tuple[float, float]:
        if current_time is None:
            current_time = time.perf_counter()
        
        elapsed_start: float = current_time - self._time_start
        elapsed_check: float = current_time - self._time_last
        
        return elapsed_start, elapsed_check

    def __init__(self, *, strict: bool = True):
        # _getframe(1) — фрейм того, кто создал экземпляр
        self._frame = sys._getframe(1)
        self._code = self._frame.f_code          # идентификатор функции
        self._strict = strict
        
        self._time_start: float = time.perf_counter()   # монотонные часы
        self._time_last = self._time_start
        
        self._time_list: list[tuple[float, float, str | None]] = []

    def __call__(self, messages: str | None = None) -> None:
        caller = sys._getframe(1)
        if self._strict and caller.f_code is not self._code:
            raise RuntimeError(
                f"TimeTracer вызван из '{caller.f_code.co_name}', "
                f"а привязан к '{self._code.co_name}'"
            )
            
        
        current_time = time.perf_counter()
        self._time_list.append((*self.__time_now(current_time), messages))
        self._time_last = current_time

    def reset(self) -> None:
        """Перезапустить отсчёт."""
        self._time_start = time.perf_counter()
        self._time_last = self._time_start

    @property
    def elapsed(self) -> tuple[float, float]:
        return self.__time_now()
    
    @property
    def elapsed_p(self) -> None:
        elapsed_start, elapsed_check = self.__time_now()
        print (f"{elapsed_start:.2f, {elapsed_check:.2f}}" )
        
    def report(self):
        for time_messages in self._time_list:
            elapsed_start, elapsed_check= time_messages[0], time_messages[1]
            messages = time_messages[2] or ""
            print(f"{elapsed_start:.3f}, {elapsed_check:.6f}, {messages}")