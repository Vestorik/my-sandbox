import contextlib
import functools
import inspect
import threading
from collections.abc import Callable

import yappi
from pyinstrument import Profiler


def pyinstrument_prof_decorator(func: Callable):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def awrapper(*args, **kwargs):
            prof = Profiler(async_mode="enabled")
            prof.start()
            try:
                return await func(*args, **kwargs)
            finally:
                prof.stop()
                prof.print(show_all=False)
        return awrapper
    
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            prof = Profiler()
            prof.start()
            try:
                return func(*args, **kwargs)
            finally:
                prof.stop()
                prof.print(show_all=False)
        return wrapper


_LOCK_YAPPI = threading.Lock()
_DEPTH_YAPPI = 0


@contextlib.contextmanager
def yappi_profiled(
    clock_type: str = "wall", limit: int = 30, build_graph: bool = False
):
    """Потокобезопасный контекст профилирования.

    Вложенные входы просто увеличивают счётчик: start/stop и отчёт
    делает только самый внешний уровень.
    """
    global _DEPTH_YAPPI

    _LOCK_YAPPI.acquire()
    try:
        _DEPTH_YAPPI += 1
        if _DEPTH_YAPPI == 1:
            yappi.clear_stats()
            yappi.set_clock_type(clock_type)
            yappi.start()
    finally:
        _LOCK_YAPPI.release()

    try:
        yield
    finally:
        _LOCK_YAPPI.acquire()
        try:
            _DEPTH_YAPPI -= 1
            if _DEPTH_YAPPI == 0:
                yappi.stop()
                
                # ncall (number of calls)
                # tsub (subtime, время «подфункции»)
                # ttot (total time, полное время) 
                # tavg (average time, среднее время) 
                
                stats = yappi.get_func_stats().sort("ttot", "desc")
                stats.print_all(limit=limit)

                # граф вызовов: кто кого вызвал и сколько раз
                if build_graph:
                    print("\n--- call graph ---")
                    for st in stats:
                        for child in st.children:
                            print(
                                f"{st.full_name} -> {child.full_name}  "
                                f"ncall={child.ncall}  ttot={child.ttot:.4f}"
                            )
        finally:
            _LOCK_YAPPI.release()


def yappi_prof_decor(clock_type: str = "wall", limit: int = 30,  build_graph: bool = False):
    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def awrapper(*args, **kwargs):
                with yappi_profiled(clock_type, limit, build_graph):
                    return await func(*args, **kwargs)

            return awrapper
        
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with yappi_profiled(clock_type, limit, build_graph):
                    return func(*args, **kwargs)

            return wrapper

    return decorator
