from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register("opportunities", views.OpportunityViewSet)
router.register("people", views.PersonViewSet)
router.register("communications", views.CommunicationViewSet)
router.register("status-changes", views.StatusChangeViewSet)
router.register("rounds", views.RoundViewSet)
router.register("documents", views.DocumentViewSet)
router.register("notes", views.NoteViewSet)
router.register("goals", views.GoalViewSet)

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("summary/", views.SummaryView.as_view()),
    path("", include(router.urls)),
]
