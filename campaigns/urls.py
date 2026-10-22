from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    path("", views.campaign_list, name="list"),
    path("campaigns/<int:pk>/", views.campaign_detail, name="detail"),
    path("campaigns/<int:pk>/add-creator/", views.add_creator, name="add_creator"),
    path("campaigns/<int:pk>/send-reminders/", views.send_reminders, name="send_reminders"),
    path("campaigns/<int:pk>/report.csv", views.export_csv, name="export_csv"),
    path("assignments/<int:pk>/shipping/", views.update_shipping, name="update_shipping"),
]
