import json

from django.core.management.base import BaseCommand, CommandError

from apps.weather.services import import_all


class Command(BaseCommand):
    help = "Import processed HeatSafe weather, heat-index, daily, evaluation, and prediction data."

    def handle(self, *args, **options):
        try:
            summary = import_all()
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(json.dumps(summary, indent=2)))
