# Creator Campaign Hub

A small Django app for running influencer **product-seeding campaigns** from start to finish:

**brief → select creators → ship product → collect content → report**

**Live read-only demo:** https://d130903.github.io/creator-campaign-hub/

> All brands, creators and numbers in the demo are made up (`python manage.py seed_demo`).

## What it does

| Step | Feature |
|---|---|
| Brief | A brand sets up a campaign: product, brief, target niche (picked from a fixed list), dates and how many creators it needs |
| Select creators | Creators are ranked by **engagement rate** (likes + comments ÷ followers), doubled for a niche match. A small account with an engaged audience beats a big, quiet one |
| Ship product | Each creator's product moves **Pending → Shipped → Delivered**, with a tracking number. The delivery date is recorded automatically |
| Collect content | Posts, reels and stories are logged against the creator, with likes, comments and views |
| Chase | Finds creators who got the product **7+ days ago but haven't posted**, and emails them a friendly reminder (at most once a week). Runs **every morning** on a schedule |
| Report | Each campaign shows creators, deliveries, content collection rate, views and engagement, plus a **CSV export** for the brand |

Every page needs a **signed-in team member** (Django's built-in sign-in). The team can manage everything in the Django admin (`/admin/`).

## Run it locally

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo           # fictional demo data
python manage.py createsuperuser     # your sign-in, also used for /admin/
python manage.py runserver
```

Useful commands:

```bash
python manage.py send_reminders --dry-run   # who would get a reminder today
python manage.py send_reminders             # send them (the daily schedule runs this)
python manage.py export_static              # rebuild the read-only demo in docs/
python manage.py test                       # run the tests
```

## Email

In development, emails print to the console. To send real email through **SendGrid**, set
`SENDGRID_API_KEY` and the app switches to SendGrid's SMTP relay (see `hub_project/settings.py`).

## Payments (Stripe, test mode)

Each campaign has a fee the brand pays RISER. The **Pay with card** button on a campaign page sends
the brand to a **Stripe Checkout** page, so card details never touch this app. When Stripe sends the
brand back, the app asks Stripe directly whether the payment went through before marking the campaign
paid, so a faked link can't mark anything paid.

To try it, create a free Stripe account, copy the **test** secret key (`sk_test_...`), and run:

```
set STRIPE_SECRET_KEY=sk_test_...
python manage.py runserver
```

Pay with Stripe's test card `4242 4242 4242 4242`, any future date and any CVC. The app refuses
live keys (`sk_live_...`), so no real money can move from this demo. Paying creators would be the
next step, using Stripe Connect.

## Daily reminders

`.github/workflows/daily-reminders.yml` runs `send_reminders` every morning at 9am Melbourne time,
and it can also be started by hand from the Actions tab. For the demo, it runs against fresh sample
data and the emails print to the log. For real use, point it (or a cron job on the server) at the
real database and add `SENDGRID_API_KEY` as a secret. The once-a-week rule means a repeat run never
emails the same creator twice.

## How it's built

- **Python + Django 6.1**, SQLite for development
- Business logic lives in `campaigns/services.py` (creator ranking, campaign report, who to chase). The views stay thin, and the logic is easy to test
- **23 automated tests** in `campaigns/tests.py` cover the maths, the reminder rules, sign-in, payments and the views. Stripe is faked in the tests, so they never call the internet. For example, a GET request can't change data, a signed-out visitor is sent to sign in, and a niche that isn't on the list is rejected
- **GitHub Actions** runs the checks and the tests on every push (`.github/workflows/tests.yml`)
- The demo on GitHub Pages is the real Django templates rendered to static HTML by `export_static`

## Built with AI

This project was built AI-first, with **Claude** as the coding partner. The business rules are written in plain English in `campaigns/services.py`: rank by engagement, not followers; chase after 7 days; at most one reminder a week. Each rule has a test, so it's clear the code does what the rules say.

## Ideas for next steps

- Pull follower and engagement numbers from the Instagram API instead of entering them
- Shipping status from the courier's tracking API
- A creator-facing page to upload content directly
- Deploy on a small cloud server (e.g. DigitalOcean) with PostgreSQL
