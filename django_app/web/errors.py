from django.shortcuts import render
from django.http import HttpResponseNotFound

def handler404(request, exception=None):
    return HttpResponseNotFound(render(request, "web/pages/404.jinja"))
