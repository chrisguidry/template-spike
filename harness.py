import asyncio
import random
import time

from user_templates import render_user_template, template_pool

OUTSTANDING = 128


GOOD = (
    "{{ i }} - good: {{ time }}"
    "{% for i in range(100) %}"
    "{% for j in range(100) %}"
    "{% endfor %}"
    "{% endfor %}"
)
BAD_CPU = (
    "{{ i }} - bad_cpu:  {{time}}"
    "{% for i in range(1000) %}"
    "{% for j in range(1000) %}"
    "{% for k in range(1000) %}"
    "{% for l in range(1000) %}"
    "{% endfor %}"
    "{% endfor %}"
    "{% endfor %}"
    "{% endfor %}"
)
BAD_RAM = (
    "{{ i }} - bad_ram:  {{time}}"
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


async def run():
    with template_pool():
        futures = []

        i = 1
        while True:
            template = GOOD
            if random.random() < 0.01:
                template = BAD_CPU
            elif random.random() < 0.02:
                template = BAD_RAM

            context = {"i": i, "time": time.time()}

            futures.append(render_user_template(template, context))
            i += 1

            if len(futures) > OUTSTANDING:
                rendered = await futures.pop()
                if i % 100 == 0:
                    print("Rendered", i, "templates")
                if rendered.startswith("Rendering the template"):
                    if "bad_cpu" not in rendered and "bad_ram" not in rendered:
                        print(rendered)


if __name__ == "__main__":
    asyncio.run(run())
