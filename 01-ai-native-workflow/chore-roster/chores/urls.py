from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("members", api.MemberViewSet)
router.register("chores", api.ChoreViewSet)
router.register("completions", api.CompletionViewSet)

app_name = "chores"

urlpatterns = [
    path("api/", include(router.urls)),
    path("api/dashboard/", api.dashboard, name="dashboard"),
    path("api/stats/", api.stats, name="stats"),
    # SPA entrypoint — all non-API routes render the frontend shell
    path("", TemplateView.as_view(template_name="index.html"), name="app"),
]
