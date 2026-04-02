import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import ContentBlock


@require_POST
def cms_update(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "forbidden"}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

    page = (payload.get("page") or "").strip()
    key = (payload.get("key") or "").strip()
    content = payload.get("content", "")

    if not page or not key:
        return JsonResponse({"success": False, "error": "missing_fields"}, status=400)

    block, _ = ContentBlock.objects.update_or_create(
        page=page,
        key=key,
        defaults={"content": content},
    )
    return JsonResponse({"success": True, "content": block.content})
