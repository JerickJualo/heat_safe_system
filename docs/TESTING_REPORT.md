# Final Testing Report

Verification date: November 19, 2026 (Asia/Singapore client context).

## Automated results

| Check | Result |
|---|---|
| Python unit tests | 12 passed |
| Django backend/frontend tests | 8 passed |
| `manage.py check` | Passed |
| `manage.py check --deploy` | Passed with production-style environment variables |
| `makemigrations --check --dry-run` | No changes detected |
| `migrate --check` | No unapplied migrations |
| `pip check` | No broken requirements |
| Python compilation | Passed |
| JavaScript syntax check | Passed |
| Saved-model inference | Numeric predictions for all three locations |

## Covered areas

- Heat-index simple formula, Rothfusz regression, humidity adjustments, and PAGASA boundaries.
- Timestamp timezone conversion, missing-value flags, range validation, daily aggregation, and daytime coverage.
- ML next-day target construction, previous-only rolling features, leakage checks, and chronological splits.
- Django routes, PostgreSQL-backed API responses, CSV export, invalid date/location handling, and CSRF enforcement.
- Production secret-key validation and secure settings.
- Frontend page routing and JavaScript syntax.

## Integration evidence

- Six website routes returned HTTP 200 during a fresh development-server verification.
- PostgreSQL health returned `{"status": "ok", "database": true}`.
- Model-performance API returned six evaluation records and 1,620 held-out prediction rows.
- Filtered CSV export returned the expected Davao records for a two-day date range.

## Remaining verification limitation

The Windows visual-browser helper was unavailable during the final automated run. Responsive behavior was checked through the implemented CSS breakpoints and mobile-sidebar rules, but no screenshot-based visual claim is made. A human should perform one final desktop and narrow-window visual walkthrough before public presentation.
