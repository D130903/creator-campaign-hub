from datetime import date, timedelta
from io import StringIO
from decimal import Decimal

from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Assignment, Brand, Campaign, ContentPost, Creator

TODAY = date(2026, 10, 22)


def make_creator(handle, niche="food", followers=10_000, likes=300, comments=20):
    return Creator.objects.create(
        handle=handle, name=f"{handle.title()} Test", email=f"{handle}@example.com", niche=niche,
        suburb="Fitzroy", followers=followers, avg_likes=likes, avg_comments=comments,
    )


class CampaignTestCase(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Test Bakery", category="food", contact_email="b@example.com")
        self.campaign = Campaign.objects.create(
            brand=self.brand, name="Loaf Launch", product="Sourdough", brief="Post an unboxing.",
            target_niche="food", start_date=TODAY - timedelta(days=20), end_date=TODAY + timedelta(days=10),
            status=Campaign.Status.LIVE,
        )


class EngagementRateTests(TestCase):
    def test_rate_is_likes_plus_comments_over_followers(self):
        self.assertEqual(make_creator("a", followers=10_000, likes=300, comments=20).engagement_rate, Decimal("3.20"))

    def test_zero_followers_does_not_divide_by_zero(self):
        self.assertEqual(make_creator("b", followers=0).engagement_rate, Decimal("0"))


class RecommendCreatorsTests(CampaignTestCase):
    def test_niche_match_beats_slightly_higher_engagement(self):
        food = make_creator("food", niche="food", likes=300)      # 3.2% x2 for match = 6.4
        beauty = make_creator("beauty", niche="beauty", likes=500)  # 5.2%, no match
        ranked = [r["creator"] for r in services.recommend_creators(self.campaign)]
        self.assertEqual(ranked, [food, beauty])

    def test_creators_already_on_campaign_are_excluded(self):
        on = make_creator("on")
        off = make_creator("off")
        Assignment.objects.create(campaign=self.campaign, creator=on)
        ranked = [r["creator"] for r in services.recommend_creators(self.campaign)]
        self.assertEqual(ranked, [off])


class CampaignReportTests(CampaignTestCase):
    def test_report_counts_and_rates(self):
        posted = Assignment.objects.create(
            campaign=self.campaign, creator=make_creator("p", followers=10_000),
            shipping_status=Assignment.Shipping.DELIVERED, delivered_on=TODAY - timedelta(days=9),
        )
        Assignment.objects.create(
            campaign=self.campaign, creator=make_creator("q"),
            shipping_status=Assignment.Shipping.DELIVERED, delivered_on=TODAY - timedelta(days=9),
        )
        Assignment.objects.create(campaign=self.campaign, creator=make_creator("r"))
        ContentPost.objects.create(assignment=posted, url="https://example.com/1", format="reel",
                                   posted_on=TODAY, likes=450, comments=50, views=8_000)

        report = services.campaign_report(self.campaign)

        self.assertEqual(report["creators"], 3)
        self.assertEqual(report["delivered"], 2)
        self.assertEqual(report["with_content"], 1)
        self.assertEqual(report["collection_rate"], Decimal("50.0"))
        self.assertEqual(report["views"], 8_000)
        self.assertEqual(report["engagement_rate"], Decimal("5.0"))  # 500 / 10,000 reach

    def test_empty_campaign_reports_zeros(self):
        report = services.campaign_report(self.campaign)
        self.assertEqual(report["collection_rate"], Decimal("0"))
        self.assertEqual(report["engagement_rate"], Decimal("0"))


class RemindersTests(CampaignTestCase):
    def deliver(self, handle, days_ago, reminded_days_ago=None):
        return Assignment.objects.create(
            campaign=self.campaign, creator=make_creator(handle),
            shipping_status=Assignment.Shipping.DELIVERED, delivered_on=TODAY - timedelta(days=days_ago),
            last_reminder_on=TODAY - timedelta(days=reminded_days_ago) if reminded_days_ago is not None else None,
        )

    def test_only_overdue_creators_without_content_are_chased(self):
        overdue = self.deliver("overdue", days_ago=8)
        self.deliver("recent", days_ago=3)
        posted = self.deliver("posted", days_ago=10)
        ContentPost.objects.create(assignment=posted, url="https://example.com/2", format="post", posted_on=TODAY)
        self.deliver("nagged", days_ago=12, reminded_days_ago=2)

        self.assertEqual(services.creators_to_chase(self.campaign, TODAY), [overdue])

    def test_send_reminder_emails_creator_and_records_date(self):
        assignment = self.deliver("chase", days_ago=8)
        services.send_reminder(assignment, TODAY)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["chase@example.com"])
        self.assertIn("Sourdough", mail.outbox[0].body)
        assignment.refresh_from_db()
        self.assertEqual(assignment.last_reminder_on, TODAY)


class ViewTests(CampaignTestCase):
    def test_list_and_detail_pages_load(self):
        self.assertContains(self.client.get(reverse("campaigns:list")), "Loaf Launch")
        self.assertContains(self.client.get(self.campaign.get_absolute_url()), "Recommended creators")

    def test_add_creator_is_idempotent(self):
        creator = make_creator("new")
        url = reverse("campaigns:add_creator", args=[self.campaign.pk])
        self.client.post(url, {"creator": creator.pk})
        self.client.post(url, {"creator": creator.pk})
        self.assertEqual(self.campaign.assignments.count(), 1)

    def test_marking_delivered_sets_delivery_date(self):
        assignment = Assignment.objects.create(campaign=self.campaign, creator=make_creator("ship"))
        self.client.post(reverse("campaigns:update_shipping", args=[assignment.pk]),
                         {"shipping_status": "delivered", "tracking_number": "AP123"})
        assignment.refresh_from_db()
        self.assertEqual(assignment.shipping_status, "delivered")
        self.assertEqual(assignment.tracking_number, "AP123")
        self.assertIsNotNone(assignment.delivered_on)

    def test_unknown_shipping_status_is_rejected(self):
        assignment = Assignment.objects.create(campaign=self.campaign, creator=make_creator("bad"))
        self.client.post(reverse("campaigns:update_shipping", args=[assignment.pk]), {"shipping_status": "lost"})
        assignment.refresh_from_db()
        self.assertEqual(assignment.shipping_status, "pending")

    def test_get_cannot_change_data(self):
        response = self.client.get(reverse("campaigns:send_reminders", args=[self.campaign.pk]))
        self.assertEqual(response.status_code, 405)

    def test_csv_export(self):
        Assignment.objects.create(campaign=self.campaign, creator=make_creator("csv"))
        response = self.client.get(reverse("campaigns:export_csv", args=[self.campaign.pk]))
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("@csv", response.content.decode())


class SeedDemoTests(TestCase):
    def test_seed_demo_is_repeatable(self):
        call_command("seed_demo", seed=1, stdout=StringIO())
        first = list(Creator.objects.values_list("handle", flat=True))
        call_command("seed_demo", seed=1, stdout=StringIO())
        self.assertEqual(first, list(Creator.objects.values_list("handle", flat=True)))
        self.assertEqual(Campaign.objects.count(), 3)
