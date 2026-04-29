from jinja2 import Environment, ChoiceLoader, PackageLoader, ChainableUndefined
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from django.utils import formats

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
        "serviceName": "Help to stay healthy",
    })

    def nhs_date(value):
        """
        Formats a datetime like: Monday 28 Dec 2025
        (i.e. dddd d MMM yyyy)
        """
        if not value:
            return ""
        return f"{formats.date_format(value, 'l j M Y')}"

    env.filters["nhs_date"] = nhs_date

    return env
