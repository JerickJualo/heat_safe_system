from django.shortcuts import render


def landing_page(request):
    """Render the initial HeatSafe landing page."""
    return render(request, "core/landing.html")
