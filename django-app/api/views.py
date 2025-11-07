from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from .models import Item
import json
import logging

log = logging.getLogger("django.request")

# Public
def public_ping(request):
    return HttpResponse("pong", content_type="text/plain")

# Secure endpoints (auth enforced by core.middleware.RequireCognitoJWTForSecure)

@require_http_methods(["GET"])
def items(request):
    data = list(Item.objects.values("item_id", "value").order_by("item_id"))
    return JsonResponse({"items": data})

@csrf_exempt
@require_http_methods(["GET", "POST"])
def item_detail(request, item_id: int):
    try:
        if request.method == "GET":
            try:
                obj = Item.objects.values("item_id", "value").get(item_id=item_id)
                return JsonResponse(obj, status=200)
            except Item.DoesNotExist:
                return JsonResponse({"error": "Not found"}, status=404)

        # POST → upsert
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        value = body.get("value")
        if not isinstance(value, str):
            return JsonResponse({"error": "`value` (string) is required"}, status=400)

        with transaction.atomic():
            obj, created = Item.objects.update_or_create(
                item_id=item_id, defaults={"value": value[:255]}
            )

        return JsonResponse(
            {"item_id": obj.item_id, "value": obj.value, "created": created},
            status=201 if created else 200,
        )

    # No DRF here, catch all unexpected errors
    except Exception as e:
        log.exception("Unhandled in item_detail")
        return JsonResponse({"error": f"server error: {e}"}, status=500)
