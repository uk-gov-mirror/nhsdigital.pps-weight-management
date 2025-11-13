from jinja2 import Environment
from django.urls import reverse
from django.templatetags.static import static as dj_static

def environment(**options):
    env = Environment(**options)
    env.globals.update({'url': reverse, 'static': dj_static})
    return env
