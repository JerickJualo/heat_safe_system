"""Exercise Phase 5 endpoints against the configured Django database."""

from django.test import Client


def main() -> int:
    client = Client(HTTP_HOST="localhost")
    paths = [
        "/api/health/",
        "/api/dashboard/",
        "/api/analytics/?location=surigao_city&limit=2",
        "/api/predictions/?location=surigao_city",
        "/api/locations/compare/",
        "/api/report/",
    ]
    for path in paths:
        response = client.get(path)
        payload = response.json()
        print(path, response.status_code)
        if path == "/api/dashboard/":
            print("dashboard_locations=", len(payload["locations"]))
        elif path.startswith("/api/analytics"):
            print("analytics_count=", payload["count"], "sample=", payload["records"][0])
        elif path.startswith("/api/locations/compare"):
            print("comparison_date=", payload["date"], "locations=", len(payload["locations"]))
        elif path == "/api/report/":
            print("report_counts=", payload["counts"])
        else:
            print(payload)
    response = client.post("/api/predictions/generate/")
    print("/api/predictions/generate/", response.status_code, response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
