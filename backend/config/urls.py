from django.urls import include, path

handler404 = "trips.api.views.not_found"

urlpatterns = [path("api/", include("trips.api.urls"))]
