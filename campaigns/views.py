import csv
from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Assignment, Campaign, Creator


def campaign_list(request):
    campaigns = Campaign.objects.select_related("brand")
    rows = [{"campaign": c, "report": services.campaign_report(c)} for c in campaigns]
    return render(request, "campaigns/campaign_list.html", {"rows": rows})


def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign.objects.select_related("brand"), pk=pk)
    assignments = campaign.assignments.select_related("creator").prefetch_related("posts")
    return render(request, "campaigns/campaign_detail.html", {
        "campaign": campaign,
        "assignments": assignments,
        "report": services.campaign_report(campaign),
        "recommended": services.recommend_creators(campaign, limit=5),
        "to_chase": services.creators_to_chase(campaign, date.today()),
        "shipping_choices": Assignment.Shipping.choices,
    })


@require_POST
def add_creator(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    creator = get_object_or_404(Creator, pk=request.POST.get("creator"))
    _, created = Assignment.objects.get_or_create(campaign=campaign, creator=creator)
    if created:
        messages.success(request, f"Added {creator} to the campaign.")
    else:
        messages.info(request, f"{creator} is already on this campaign.")
    return redirect(campaign)


@require_POST
def update_shipping(request, pk):
    assignment = get_object_or_404(Assignment, pk=pk)
    status = request.POST.get("shipping_status")
    if status not in Assignment.Shipping.values:
        messages.error(request, "Unknown shipping status.")
        return redirect(assignment.campaign)
    assignment.shipping_status = status
    assignment.tracking_number = request.POST.get("tracking_number", assignment.tracking_number).strip()
    if status == Assignment.Shipping.DELIVERED and not assignment.delivered_on:
        assignment.delivered_on = date.today()
    assignment.save()
    messages.success(request, f"{assignment.creator}: shipping set to {assignment.get_shipping_status_display()}.")
    return redirect(assignment.campaign)


@require_POST
def send_reminders(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    due = services.creators_to_chase(campaign, date.today())
    for assignment in due:
        services.send_reminder(assignment, date.today())
    messages.success(request, f"Sent {len(due)} reminder email(s).")
    return redirect(campaign)


def export_csv(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="campaign-{campaign.pk}-report.csv"'
    writer = csv.writer(response)
    writer.writerow(["creator", "followers", "shipping", "posts", "likes", "comments", "views", "post_urls"])
    for a in campaign.assignments.select_related("creator").prefetch_related("posts"):
        posts = list(a.posts.all())
        writer.writerow([
            f"@{a.creator.handle}", a.creator.followers, a.shipping_status, len(posts),
            sum(p.likes for p in posts), sum(p.comments for p in posts), sum(p.views for p in posts),
            " ".join(p.url for p in posts),
        ])
    return response
