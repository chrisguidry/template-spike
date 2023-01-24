import asyncio
import random
import time

from user_templates import render_user_template, template_pool

OUTSTANDING = 32


GOOD = "{{ i }} - good: {{ time }}"
BAD = (
    "{{ i }} - bad:  {{time}}"
    "{% for i in range(1000) %}"
    "{% for j in range(1000) %}"
    "{% for k in range(1000) %}"
    "{% for l in range(1000) %}"
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
                template = BAD

            context = {"i": i, "time": time.time()}

            futures.append(render_user_template(template, context))
            i += 1

            if len(futures) > OUTSTANDING:
                rendered = await futures.pop()
                print(rendered)


if __name__ == "__main__":
    asyncio.run(run())
