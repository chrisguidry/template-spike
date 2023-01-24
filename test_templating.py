from typing import Any

import pytest

from user_templates import (
    register_user_template_filters,
    render_user_template,
    template_pool,
)


def excitable(value: Any) -> str:
    return f"{value}!!!"


register_user_template_filters({"excitable": excitable})


@pytest.fixture(scope="module", autouse=True)
def open_template_pool():
    with template_pool():
        yield


async def test_basic_template_is_fine():
    template = "{{ greeting }}"
    rendered = await render_user_template(template, {"greeting": "Hello"})
    assert rendered == "Hello"


async def test_has_access_to_registered_filters():
    template = "{{ greeting|excitable }}"
    rendered = await render_user_template(template, {"greeting": "Hello"})
    assert excitable("Hello") == "Hello!!!"
    assert rendered == "Hello!!!"


async def test_grindy_template_is_prohibited():
    # Even with the MAX_RANGE, it's possible to create nested loops that far exceed
    # that limit.  For these, we'll block on overall CPU time spent.  To test this case,
    # ensure there's no additional whitespace or data to render, so this is only
    # grinding on CPU but won't overflow memory.
    template = (
        "{% for i in range(1000) %}"
        "{% for j in range(1000) %}"
        "{% for k in range(1000) %}"
        "{% for l in range(1000) %}"
        "{% endfor %}"
        "{% endfor %}"
        "{% endfor %}"
        "{% endfor %}"
    )
    rendered = await render_user_template(template, {})
    assert rendered.startswith(
        "Rendering the template exceeded the CPU, memory, or time limit."
    )


async def test_nightmare_template_is_prohibited():
    # To test this case, use a similarly horrible template as the CPU case, but actually
    # try to produce some output ("hey there bud")
    template = (
        "{% for i in range(1000) %}"
        "{% for j in range(1000) %}"
        "{% for k in range(1000) %}"
        "{% for l in range(1000) %}"
        "hey there bud"
        "{% endfor %}"
        "{% endfor %}"
        "{% endfor %}"
        "{% endfor %}"
    )
    rendered = await render_user_template(template, {})
    assert rendered.startswith(
        "Rendering the template exceeded the CPU, memory, or time limit."
    )
