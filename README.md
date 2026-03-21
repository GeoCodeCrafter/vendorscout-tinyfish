# VendorScout

VendorScout is a TinyFish-powered procurement assistant built for the TinyFish $2M Pre-Accelerator Hackathon. It launches live browser automations against multiple vendor sites, searches for a product, and turns the results into a buyer-friendly comparison dashboard.

## Why This Fits The Contest

- It performs real work on the live web instead of wrapping a static dataset.
- It uses multi-step browser automation: navigation, pop-up handling, site search, and extraction.
- It solves a business workflow buyers and procurement teams already spend time on manually.
- It produces a clean demo in under 3 minutes.

## Core Workflow

1. Enter a product name or SKU.
2. Paste at least two vendor URLs.
3. Launch TinyFish runs against each site.
4. Poll status until the structured results come back.
5. Compare the live offers in one view and export CSV.

## Project Structure

- `app.py`: lightweight Python web server and API routes
- `tinyfish_client.py`: TinyFish API wrapper using the official HTTP endpoints
- `workflow.py`: prompt construction and result normalization
- `static/`: frontend assets
- `tests/`: small unit tests for prompt and parsing logic

## Quick Start

1. Copy `.env.example` to `.env`
2. Set `TINYFISH_API_KEY` in `.env`
3. Start the app:

```bash
python3 app.py
```

4. Open `http://localhost:8000`

## Environment Variables

- `TINYFISH_API_KEY`: required
- `TINYFISH_BASE_URL`: optional, defaults to `https://agent.tinyfish.ai`
- `PORT`: optional, defaults to `8000`

## Demo Script

Use this for a fast contest demo:

- Product: `Sony WH-1000XM5`
- Vendors:
  - `https://www.bestbuy.com/`
  - `https://www.target.com/`
  - `https://www.bhphotovideo.com/`
- Buyer notes: `Prefer in-stock listings and mention shipping timing if visible.`

Demo flow:

1. Explain the problem: buyer ops teams manually check multiple supplier sites.
2. Start a scan from the dashboard.
3. Show that each run is independent and live.
4. Wait for completed results and point out the cheapest vendor.
5. Export the CSV as the handoff artifact a buyer could use.

## Submission Checklist

- Record a raw 2-3 minute demo of the app doing live work on real vendor sites.
- Post the demo publicly on X and tag `@Tiny_fish`.
- Submit the HackerEarth project page with:
  - product overview
  - GitHub repo link
  - X post link
  - short problem and solution write-up

## Notes

- The app defaults to `stealth` browser profile because live retail websites often use anti-bot measures.
- If you want different geography, provide a country code like `US` in the form.
- TinyFish results can vary slightly by site, so the app normalizes structured output before rendering it.
