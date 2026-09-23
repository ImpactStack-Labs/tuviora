# API Contracts

## Events API

The Events API provides the shared event resource used by the Tuviora
organizer dashboard and other backend features.

### Base endpoint

`/api/events/`

### Authentication

The endpoint requires an authenticated Django user.

The backend determines the event organizer from the authenticated user.

The frontend must not submit an organizer ID when creating an event.

### GET /api/events/

Returns the authenticated organizer's events.

Example response:

```json
[
  {
    "id": 1,
    "name": "Tuviora Hackathon",
    "category": "hackathon",
    "description": "An event operations hackathon.",
    "date": "2026-10-01",
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "event_format": "physical",
    "venue": "Uganda Christian University",
    "landmark": "Mukono",
    "latitude": "0.353600",
    "longitude": "32.755300",
    "online_platform": "",
    "online_url": "",
    "joining_instructions": "",
    "capacity": 100,
    "organizer": 1,
    "status": "draft",
    "created_at": "2026-09-23T10:00:00Z",
    "updated_at": "2026-09-23T10:00:00Z"
  }
]