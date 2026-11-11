from django.contrib import admin

from .models import Assignment, Brand, Campaign, ContentPost, Creator, Payment


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "contact_email"]


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    list_display = ["handle", "name", "niche", "suburb", "followers", "engagement_rate"]
    list_filter = ["niche"]
    search_fields = ["handle", "name"]


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "status", "fee", "is_paid", "start_date", "end_date"]
    list_filter = ["status", "brand"]
    inlines = [AssignmentInline]


class ContentPostInline(admin.TabularInline):
    model = ContentPost
    extra = 0


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["creator", "campaign", "shipping_status", "delivered_on", "last_reminder_on"]
    list_filter = ["shipping_status", "campaign"]
    inlines = [ContentPostInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["campaign", "amount", "status", "created_at", "paid_at"]
    list_filter = ["status"]
    readonly_fields = ["stripe_session_id", "created_at", "paid_at"]
