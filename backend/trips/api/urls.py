from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view()),
    path("geocode/", views.GeocodeView.as_view()),
    path("trips/prepare/", views.PrepareTripView.as_view()),
    path("trips/score/", views.ScoreTripView.as_view()),
    path("trips/analyze/", views.AnalyzeTripView.as_view()),
]
