from jinja2 import Environment, ChoiceLoader, PackageLoader, ChainableUndefined
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse

def environment(**options):
    options["undefined"] = ChainableUndefined

    env = Environment(**options)

    env.loader = ChoiceLoader([
        env.loader,
        PackageLoader("nhsuk_frontend_jinja", "templates"),
    ])

    env.globals.update({
        "static": staticfiles_storage.url,
        "url": reverse,
    })

    return env
