# PD-10: Competitor Raw Ads Browser

## Goal
Let users browse all 226 scraped competitor ads from Meta Ad Library, filtered by competitor and attributes.

## Deliverables
1. **`app/api/routes/competitive.py`** — New API route file
   - `GET /api/competitive/ads` — reads `data/competitive/raw/{competitor}.json`, returns ads
   - Query params: `?competitor=Chegg&hook_type=question&audience=parents`
2. **`app/api/main.py`** — Register competitive router
3. **`app/frontend/src/views/CompetitiveIntelPage.tsx`** — Expand competitor cards to show raw ads on click

## Raw Ad Data Format (from `data/competitive/raw/*.json`)
```json
{
  "Ad Library ID": "777924175318035",
  "Ad URL": "https://www.facebook.com/ads/library/?...",
  "Ad Creative Image": "https://scontent-dfw5-2.xx.fbcdn.net/...",
  "Ad Text Content": "You deserve learning built around you...",
  "Advertiser Name": "Chegg",
  "Started Running Date": "01/20/26",
  "Platforms": "Facebook\nInstagram\nAudience Network\nMessenger"
}
```

## Frontend Features
- Click competitor card → expands to show their raw ads
- Each ad card: ad text, hook type badge, platform, date, creative image (from Meta CDN URL)
- Filter within a competitor's ads by hook type, audience, tone
- Masonry layout matching Ad Library style

## Acceptance Criteria
- User can browse all 226 scraped ads filtered by competitor
- Creative images display from Meta CDN URLs
- Filter controls work within each competitor's ad set

## Dependencies
- PD-09 (standalone page must exist first)

## Estimate
~1.5 hours
