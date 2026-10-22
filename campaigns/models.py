from decimal import Decimal

from django.db import models
from django.urls import reverse


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50)
    contact_email = models.EmailField()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Creator(models.Model):
    handle = models.CharField(max_length=60, unique=True, help_text="Instagram handle, without the @")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    niche = models.CharField(max_length=50)
    suburb = models.CharField(max_length=60)
    followers = models.PositiveIntegerField()
    avg_likes = models.PositiveIntegerField(help_text="Average likes per recent post")
    avg_comments = models.PositiveIntegerField(help_text="Average comments per recent post")

    class Meta:
        ordering = ["handle"]

    def __str__(self):
        return f"@{self.handle}"

    @property
    def engagement_rate(self):
        """Average (likes + comments) per post as a percentage of followers."""
        if not self.followers:
            return Decimal("0")
        rate = Decimal(self.avg_likes + self.avg_comments) / Decimal(self.followers) * 100
        return rate.quantize(Decimal("0.01"))


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        LIVE = "live", "Live"
        COMPLETE = "complete", "Complete"

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=120)
    product = models.CharField(max_length=120)
    brief = models.TextField()
    target_niche = models.CharField(max_length=50)
    creators_needed = models.PositiveIntegerField(default=10)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.brand}: {self.name}"

    def get_absolute_url(self):
        return reverse("campaigns:detail", args=[self.pk])


class Assignment(models.Model):
    """A creator selected for a campaign, tracked from product send-out to content collected."""

    class Shipping(models.TextChoices):
        PENDING = "pending", "Pending"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="assignments")
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE, related_name="assignments")
    shipping_status = models.CharField(max_length=10, choices=Shipping.choices, default=Shipping.PENDING)
    tracking_number = models.CharField(max_length=40, blank=True)
    delivered_on = models.DateField(null=True, blank=True)
    last_reminder_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["creator__handle"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "creator"], name="one_assignment_per_creator"),
        ]

    def __str__(self):
        return f"{self.creator} on {self.campaign}"

    @property
    def has_content(self):
        return self.posts.exists()


class ContentPost(models.Model):
    class Format(models.TextChoices):
        REEL = "reel", "Reel"
        POST = "post", "Post"
        STORY = "story", "Story"

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="posts")
    url = models.URLField()
    format = models.CharField(max_length=10, choices=Format.choices)
    posted_on = models.DateField()
    likes = models.PositiveIntegerField(default=0)
    comments = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-posted_on"]

    def __str__(self):
        return f"{self.get_format_display()} by {self.assignment.creator}"
