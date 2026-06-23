from rest_framework.routers import DefaultRouter

from .views import RepositoryViewSet

router = DefaultRouter()
router.register("repositories", RepositoryViewSet, basename="repository")

urlpatterns = router.urls
