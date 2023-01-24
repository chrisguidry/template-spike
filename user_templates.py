"""Utilities to support safely rendering user-supplied templates"""

import asyncio
import multiprocessing
import resource
import time
from contextlib import contextmanager
from multiprocessing.pool import Pool
from typing import Any, Generator

import jinja2.sandbox
from jinja2 import ChainableUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

# Limit the maximum size of a range() call
jinja2.sandbox.MAX_RANGE = 1000


CPU_TIME_LIMIT = 2
TEMPLATE_TIMEOUT = float(CPU_TIME_LIMIT) + 0.5
POOL_RESTART_ALLOWANCE = 5
RENDERING_PROCESS_TIMEOUT = TEMPLATE_TIMEOUT + POOL_RESTART_ALLOWANCE
MEMORY_LIMIT = 400_000_000
PROCESSES = 4


def set_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_TIME_LIMIT, CPU_TIME_LIMIT))


_pool: Pool | None = None


@contextmanager
def template_pool(processes=PROCESSES) -> Generator[Pool, None, None]:
    """Gets a multiprocessing.Pool for rendering user-supplied Jinja2 templates."""
    global _pool

    # If we've previously opened a pool, use it...
    if _pool:
        yield _pool
        return

    # ...otherwise, start a new one and make it the global one
    with Pool(processes=processes, maxtasksperchild=1, initializer=set_limits) as pool:
        _pool = pool
        try:
            yield pool
        finally:
            _pool = None


_template_environment = ImmutableSandboxedEnvironment(
    undefined=ChainableUndefined,
)


def register_user_template_filters(filters: dict[str, Any]):
    """Register additional filters that will be available to user templates"""
    _template_environment.filters |= filters


def _render_unsafe(template: str, context: dict[str, Any]) -> str:
    loaded = _template_environment.from_string(template)
    return loaded.render(context)


def _ping() -> str:
    return "pong"


def _render_in_pool(template: str, context: dict[str, Any]) -> str:
    global _pool
    with template_pool() as pool:
        try:
            result = pool.apply_async(_render_unsafe, args=(template, context))
        except ValueError as e:
            if "Pool not running" in str(e):
                time.sleep(1)
                return _render_in_pool(template, context)
            raise

        try:
            return result.get(timeout=TEMPLATE_TIMEOUT)
        except multiprocessing.TimeoutError:
            try:
                pong = pool.apply_async(_ping)
            except ValueError as e:
                if "Pool not running" in str(e):
                    time.sleep(1)
                    return _render_in_pool(template, context)
                raise

            try:
                assert pong.get(timeout=TEMPLATE_TIMEOUT) == "pong"
            except (AssertionError, multiprocessing.TimeoutError):
                pool.__exit__(None, None, None)
                _pool = Pool(
                    processes=PROCESSES, maxtasksperchild=1, initializer=set_limits
                )
                _pool.__enter__()

                return _render_in_pool(template, context)
            else:
                raise


def validate_user_template(template: str):
    _template_environment.from_string(template)


async def render_user_template(template: str, context: dict[str, Any]) -> str:
    """Renders the given template in a process with strict CPU and memory limits"""
    if "{" not in template:
        return template

    renderer = _render_in_pool

    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, renderer, template, context)
    try:
        rendered = await asyncio.wait_for(future, timeout=RENDERING_PROCESS_TIMEOUT)
        return rendered
    except TimeoutError:
        return (
            "Rendering the template exceeded the CPU, memory, or time limit.\n"
            "TimeoutError\n"
            "Template source:\n"
        ) + template
    except asyncio.TimeoutError:
        return (
            "Rendering the template exceeded the CPU, memory, or time limit.\n"
            "asyncio.TimeoutError\n"
            "Template source:\n"
        ) + template
    except multiprocessing.TimeoutError:
        return (
            "Rendering the template exceeded the CPU, memory, or time limit.\n"
            "multiprocessing.TimeoutError\n"
            "Template source:\n"
        ) + template
    except MemoryError:
        return (
            "Rendering the template exceeded the CPU, memory, or time limit.\n"
            "MemoryError\n"
            "Template source:\n"
        ) + template
    except Exception as e:
        return (
            f"Failed to render template due to the following error: {e!r}\n"
            "Template source:\n"
        ) + template
