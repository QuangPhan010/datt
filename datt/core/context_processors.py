from types import SimpleNamespace

from .models import ContentBlock


def cms(request):
    blocks = ContentBlock.objects.all()
    data = {f"{block.page}_{block.key}": block.content for block in blocks}
    return {"cms": SimpleNamespace(**data)}
