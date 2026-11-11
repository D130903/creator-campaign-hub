"""Business logic, kept out of the views so it is easy to test and reuse."""
from datetime import timedelta
from decimal import Decimal

from django.core.mail import send_mail
from django.db.models import Sum

from .models import Assignment, Creator, Payment

REMINDER_AFTER_DAYS = 7


def recommend_creators(campaign, limit=10):
    """Rank creators who are not yet on the campaign.

    Score = engagement rate, doubled when the creator's niche matches the campaign.
    Engagement beats raw follower count: a micro-influencer whose audience actually
    responds is worth more to a product-seeding campaign than a big, quiet account.
    """
    taken = campaign.assignments.values_list("creator_id", flat=True)
    scored = []
    for creator in Creator.objects.exclude(pk__in=taken):
        match = creator.niche.lower() == campaign.target_niche.lower()
        score = creator.engagement_rate * (2 if match else 1)
        scored.append((score, match, creator))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [{"creator": c, "niche_match": m, "score": s} for s, m, c in scored[:limit]]


def campaign_report(campaign):
    """The numbers a brand asks for at the end of a campaign."""
    assignments = list(campaign.assignments.select_related("creator").prefetch_related("posts"))
    delivered = [a for a in assignments if a.shipping_status == Assignment.Shipping.DELIVERED]
    with_content = [a for a in assignments if a.has_content]
    totals = campaign.assignments.aggregate(
        likes=Sum("posts__likes"), comments=Sum("posts__comments"), views=Sum("posts__views")
    )
    likes, comments, views = (totals[k] or 0 for k in ("likes", "comments", "views"))
    reach = sum(a.creator.followers for a in with_content)
    return {
        "creators": len(assignments),
        "shipped": sum(a.shipping_status != Assignment.Shipping.PENDING for a in assignments),
        "delivered": len(delivered),
        "with_content": len(with_content),
        "collection_rate": _pct(len(with_content), len(delivered)),
        "posts": sum(a.posts.count() for a in assignments),
        "likes": likes,
        "comments": comments,
        "views": views,
        "reach": reach,
        "engagement_rate": _pct(likes + comments, reach),
    }


def creators_to_chase(campaign, today):
    """Delivered at least REMINDER_AFTER_DAYS ago, no content yet, not reminded in the last week."""
    cutoff = today - timedelta(days=REMINDER_AFTER_DAYS)
    due = []
    for a in campaign.assignments.filter(
        shipping_status=Assignment.Shipping.DELIVERED, delivered_on__lte=cutoff
    ).select_related("creator"):
        if a.has_content:
            continue
        if a.last_reminder_on and a.last_reminder_on > cutoff:
            continue
        due.append(a)
    return due


def send_reminder(assignment, today):
    creator, campaign = assignment.creator, assignment.campaign
    send_mail(
        subject=f"Quick reminder: your {campaign.brand} post",
        message=(
            f"Hi {creator.name.split()[0]},\n\n"
            f"Hope you're enjoying the {campaign.product}! It arrived on "
            f"{assignment.delivered_on:%d %b}, and we'd love to see your post when it's ready.\n\n"
            f"Brief: {campaign.brief}\n\nThanks!\nThe campaigns team"
        ),
        from_email=None,
        recipient_list=[creator.email],
    )
    assignment.last_reminder_on = today
    assignment.save(update_fields=["last_reminder_on"])


def _pct(part, whole):
    if not whole:
        return Decimal("0")
    return (Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.1"))


# --- Payments -------------------------------------------------------------------------

class PaymentsNotConfigured(Exception):
    """Raised when there's no Stripe test key, so the view can show a friendly message."""


def _stripe():
    """Return the Stripe client, refusing anything but a test-mode key."""
    import stripe
    from django.conf import settings

    key = settings.STRIPE_SECRET_KEY
    if not key.startswith("sk_test_"):
        raise PaymentsNotConfigured("Set STRIPE_SECRET_KEY to a Stripe test key (sk_test_...).")
    stripe.api_key = key
    return stripe


def start_checkout(campaign, success_url, cancel_url):
    """Create a Stripe Checkout page for the campaign fee and record a pending Payment.

    Returns (payment, url). The brand is sent to `url`, which Stripe hosts, so card
    details never pass through this app.
    """
    stripe = _stripe()
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "quantity": 1,
            "price_data": {
                "currency": "aud",
                "unit_amount": int(campaign.fee * 100),  # Stripe works in cents
                "product_data": {"name": f"Campaign fee: {campaign.name} ({campaign.brand})"},
            },
        }],
        customer_email=campaign.brand.contact_email,
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"campaign_id": str(campaign.pk)},
    )
    payment = Payment.objects.create(
        campaign=campaign, amount=campaign.fee, stripe_session_id=session.id,
    )
    return payment, session.url


def confirm_payment(campaign, session_id, now):
    """Ask Stripe whether a checkout session was paid, and mark our Payment if so.

    We never trust the browser's word that it paid: the session id only tells us which
    payment to check, and the answer comes straight from Stripe. Safe to call twice.
    """
    payment = Payment.objects.filter(campaign=campaign, stripe_session_id=session_id).first()
    if payment is None:
        return None
    if payment.status == Payment.Status.PAID:
        return payment
    session = _stripe().checkout.Session.retrieve(session_id)
    if session.payment_status == "paid":
        payment.status = Payment.Status.PAID
        payment.paid_at = now
        payment.save(update_fields=["status", "paid_at"])
    return payment
