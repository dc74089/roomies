from django.conf import settings

from app.models import SiteConfig


def add_settings(request):
    return {
        "settings": settings
    }


def add_siteconfig(request):
    return {conf.id: bool(conf) for conf in SiteConfig.objects.all()}
