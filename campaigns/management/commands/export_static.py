"""Render a read-only copy of the app into docs/ so it can be hosted on GitHub Pages."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.test import RequestFactory

from campaigns import views
from campaigns.models import Campaign


class Command(BaseCommand):
    help = "Write static HTML pages of the current data to docs/ for GitHub Pages."

    def handle(self, *args, **options):
        out = Path(settings.BASE_DIR) / "docs"
        (out / "campaigns").mkdir(parents=True, exist_ok=True)
        for old in (out / "campaigns").glob("*.html"):  # ids change when demo data is reseeded
            old.unlink()
        factory = RequestFactory()

        pages = {"index.html": views.campaign_list(self._request(factory))}
        for campaign in Campaign.objects.all():
            pages[f"campaigns/{campaign.pk}.html"] = views.campaign_detail(self._request(factory), campaign.pk)

        for name, response in pages.items():
            html = response.content.decode()
            depth = "../" if "/" in name else ""
            # Make app links work as static files.
            html = html.replace('href="/campaigns/', f'href="{depth}campaigns/').replace('href="/"', f'href="{depth}index.html"')
            for campaign in Campaign.objects.all():
                html = html.replace(f'href="{depth}campaigns/{campaign.pk}/"', f'href="{depth}campaigns/{campaign.pk}.html"')
            (out / name).write_text(html, encoding="utf-8")
        (out / ".nojekyll").write_text("")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(pages)} pages to {out}"))

    @staticmethod
    def _request(factory):
        request = factory.get("/")
        request.static_demo = True
        request._messages = []
        return request
