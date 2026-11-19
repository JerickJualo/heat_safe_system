from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.dashboard_page, name="dashboard"),
    path("analytics/", views.analytics_page, name="analytics"),
    path("prediction/", views.prediction_page, name="prediction"),
    path("comparison/", views.comparison_page, name="comparison"),
]
