from django.shortcuts import render


def _page(request, template_name: str, page_id: str, page_title: str):
    return render(
        request,
        template_name,
        {"page_id": page_id, "page_title": page_title},
    )


def dashboard_page(request):
    return _page(request, "core/dashboard.html", "dashboard", "Dashboard")


def analytics_page(request):
    return _page(request, "core/analytics.html", "analytics", "Data Analytics")


def prediction_page(request):
    return _page(request, "core/prediction.html", "prediction", "Heat Index Prediction")


def comparison_page(request):
    return _page(request, "core/comparison.html", "comparison", "Location Comparison")


def performance_page(request):
    return _page(request, "core/performance.html", "performance", "Model Performance")


def reports_page(request):
    return _page(request, "core/reports.html", "reports", "Reports and Data Sources")


landing_page = dashboard_page
