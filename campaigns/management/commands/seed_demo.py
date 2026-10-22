"""Load made-up demo data. Every brand, creator and number here is fictional."""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from campaigns.models import Assignment, Brand, Campaign, ContentPost, Creator

NICHES = {"food": "eats", "beauty": "glow", "fitness": "moves", "lifestyle": "daily",
          "parenting": "family", "wellness": "wellbeing"}
SUBURBS = ["Brunswick", "Fitzroy", "South Yarra", "Richmond", "St Kilda", "Footscray", "Carlton",
           "Northcote", "Hawthorn", "Preston", "Box Hill", "Williamstown"]
FIRST = ["Mia", "Jack", "Zara", "Leo", "Ava", "Noah", "Isla", "Kai", "Ruby", "Arjun", "Chloe", "Sam",
         "Priya", "Tom", "Lily", "Omar", "Grace", "Ethan", "Sofia", "Hugo", "Ella", "Max", "Aria", "Ben"]


class Command(BaseCommand):
    help = "Replace all data with a fictional demo set (brands, creators, campaigns, content)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=5, help="Random seed, for repeatable data")

    @transaction.atomic
    def handle(self, *args, seed, **options):
        rng = random.Random(seed)
        today = date.today()
        for model in (ContentPost, Assignment, Campaign, Creator, Brand):
            model.objects.all().delete()

        brands = [
            Brand.objects.create(name="Golden Crumb Bakery", category="food", contact_email="hello@goldencrumb.example"),
            Brand.objects.create(name="Glow Theory Skincare", category="beauty", contact_email="team@glowtheory.example"),
            Brand.objects.create(name="Stride Active", category="fitness", contact_email="collabs@strideactive.example"),
        ]

        creators = []
        for i, first in enumerate(FIRST):
            niche = list(NICHES)[i % len(NICHES)]
            followers = rng.choice([rng.randint(2_000, 9_000), rng.randint(9_000, 40_000), rng.randint(40_000, 120_000)])
            rate = rng.uniform(0.012, 0.09)  # 1.2% to 9% engagement
            likes = int(followers * rate)
            creators.append(Creator.objects.create(
                handle=f"{first.lower()}.{NICHES[niche]}{i}",
                name=f"{first} {rng.choice('ABCDEFGHJKLMNPRSTW')}.",
                email=f"{first.lower()}{i}@creator.example",
                niche=niche,
                suburb=rng.choice(SUBURBS),
                followers=followers,
                avg_likes=likes,
                avg_comments=max(1, likes // rng.randint(15, 40)),
            ))

        plans = [
            (brands[0], "Spring Sourdough Drop", "Seeded sourdough loaf", "food", Campaign.Status.LIVE, -24, 10),
            (brands[1], "Barrier Repair Serum Launch", "Barrier Repair Serum 30ml", "beauty", Campaign.Status.LIVE, -15, 8),
            (brands[2], "Run Club Socks", "Cushioned running socks (3-pack)", "fitness", Campaign.Status.DRAFT, 5, 6),
        ]
        for brand, name, product, niche, status, start_offset, needed in plans:
            start = today + timedelta(days=start_offset)
            campaign = Campaign.objects.create(
                brand=brand, name=name, product=product, target_niche=niche, creators_needed=needed,
                status=status, start_date=start, end_date=start + timedelta(days=35),
                brief=f"Unbox the {product.lower()} and share an honest first impression. Tag @{brand.name.lower().replace(' ', '')} and use #gifted.",
            )
            if status == Campaign.Status.DRAFT:
                continue
            matching = [c for c in creators if c.niche == niche]
            others = [c for c in creators if c.niche != niche]
            picked = matching + rng.sample(others, needed - len(matching))
            for creator in picked:
                self._ship_and_post(rng, campaign, creator, start, today)

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded: {Brand.objects.count()} brands, {Creator.objects.count()} creators, "
            f"{Campaign.objects.count()} campaigns, {ContentPost.objects.count()} posts."
        ))

    def _ship_and_post(self, rng, campaign, creator, start, today):
        roll = rng.random()
        if roll < 0.15:
            Assignment.objects.create(campaign=campaign, creator=creator)
            return
        if roll < 0.3:
            Assignment.objects.create(campaign=campaign, creator=creator, shipping_status=Assignment.Shipping.SHIPPED,
                                      tracking_number=f"AP{rng.randint(10**8, 10**9 - 1)}")
            return
        delivered = min(today, start + timedelta(days=rng.randint(2, 6)))
        assignment = Assignment.objects.create(
            campaign=campaign, creator=creator, shipping_status=Assignment.Shipping.DELIVERED,
            tracking_number=f"AP{rng.randint(10**8, 10**9 - 1)}", delivered_on=delivered,
        )
        if rng.random() < 0.8:
            for _ in range(rng.choice([1, 1, 2])):
                posted = min(today, delivered + timedelta(days=rng.randint(1, 9)))
                fmt = rng.choice(ContentPost.Format.values)
                likes = int(creator.avg_likes * rng.uniform(0.7, 1.5))
                ContentPost.objects.create(
                    assignment=assignment, format=fmt, posted_on=posted,
                    url=f"https://www.instagram.com/p/demo{assignment.pk}{rng.randint(100, 999)}/",
                    likes=likes, comments=max(1, likes // rng.randint(15, 40)),
                    views=int(creator.followers * rng.uniform(0.3, 1.8)) if fmt != ContentPost.Format.POST else 0,
                )
