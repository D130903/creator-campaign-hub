"""Email every creator who has had the product for a week but hasn't posted. Run daily (e.g. cron)."""
from datetime import date

from django.core.management.base import BaseCommand

from campaigns import services
from campaigns.models import Campaign


class Command(BaseCommand):
    help = "Send reminder emails to creators who received product but have not posted yet."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List who would be emailed without sending")

    def handle(self, *args, dry_run, **options):
        today = date.today()
        total = 0
        for campaign in Campaign.objects.filter(status=Campaign.Status.LIVE):
            for assignment in services.creators_to_chase(campaign, today):
                total += 1
                if dry_run:
                    self.stdout.write(f"Would remind {assignment.creator} ({campaign.name})")
                else:
                    services.send_reminder(assignment, today)
        verb = "Would send" if dry_run else "Sent"
        self.stdout.write(self.style.SUCCESS(f"{verb} {total} reminder(s)."))
