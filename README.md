# Creator Campaign Hub

A small Django app for running influencer **product-seeding campaigns** from start to finish:

**brief → select creators → ship product → collect content → report**

**Live read-only demo:** https://d130903.github.io/creator-campaign-hub/

> All brands, creators and numbers in the demo are made up (`python manage.py seed_demo`).

## What it does

| Step | Feature |
|---|---|
| Brief | A brand sets up a campaign: product, brief, target niche, dates and how many creators it needs |
| Select creators | Creators are ranked by **engagement rate** (likes + comments ÷ followers), doubled for a niche match. A small account with an engaged audience beats a big, quiet one |
| Ship product | Each creator's product moves **Pending → Shipped → Delivered**, with a tracking number. The delivery date is recorded automatically |
| Collect content | Posts, reels and stories are logged against the creator, with likes, comments and views |
| Chase | Finds creators who got the product **7+ days ago but haven't posted**, and emails them a friendly reminder (at most once a week) |
| Report | Each campaign shows creators, deliveries, content collection rate, views and engagement, plus a **CSV export** for the brand |

The team can manage everything in the Django admin (`/admin/`).

## Run it locally

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo           # fictional demo data
python manage.py createsuperuser     # for /admin/
python manage.py runserver
```

Useful commands:

```bash
python manage.py send_reminders --dry-run   # who would get a reminder today
python manage.py send_reminders             # send them (run daily, e.g. with cron)
python manage.py export_static              # rebuild the read-only demo in docs/
python manage.py test                       # run the tests
```

## Email

In development, emails print to the console. To send real email through **SendGrid**, set
`SENDGRID_API_KEY` and the app switches to SendGrid's SMTP relay (see `hub_project/settings.py`).

## How it's built

- **Python + Django 6.1**, SQLite for development
- Business logic lives in `campaigns/services.py` (creator ranking, campaign report, who to chase). The views stay thin, and the logic is easy to test
- **15 automated tests** in `campaigns/tests.py` cover the maths, the reminder rules and the views. For example, a GET request can't change data, and an unknown shipping status is rejected
- **GitHub Actions** runs the checks and the tests on every push (`.github/workflows/tests.yml`)
- The demo on GitHub Pages is the real Django templates rendered to static HTML by `export_static`

## Built with AI

This project was built AI-first, with **Claude** as the coding partner. The business rules are written in plain English in `campaigns/services.py`: rank by engagement, not followers; chase after 7 days; at most one reminder a week. Each rule has a test, so it's clear the code does what the rules say.

## Ideas for next steps

- Pull follower and engagement numbers from the Instagram API instead of entering them
- Shipping status from the courier's tracking API
- A creator-facing page to upload content directly
- Deploy on a small cloud server (e.g. DigitalOcean) with PostgreSQL
