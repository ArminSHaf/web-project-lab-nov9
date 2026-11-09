# UI Developer Guide

## API URLs

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health: `GET /health`

Use `Authorization: Bearer <access_token>` for protected endpoints.

## Required screens

### Shared

- Login
- Notifications
- Error and expired-session states

### Student

- My classes
- Active attendance: code input and QR scanner
- Location permission prompt when `location_required` is true
- Attendance confirmation result
- Attendance statistics
- Absence request form and request history

### Professor

- Class sections and enrollment
- Start attendance with duration and optional geofence
- Live confirmation list
- Cancel attendance confirmation dialog
- Absence request review
- Class statistics

## Main API actions

| UI action | Endpoint |
|---|---|
| Register during development | `POST /api/v1/auth/register` |
| Login | `POST /api/v1/auth/token` |
| Create class section | `POST /api/v1/sections` |
| Enroll a student | `POST /api/v1/sections/{section_id}/enrollments` |
| Start attendance | `POST /api/v1/attendance-sessions` |
| Confirm attendance | `POST /api/v1/attendance-sessions/{id}/confirm` |
| Cancel attendance | `POST /api/v1/attendance-sessions/{id}/cancel` |
| Request absence | `POST /api/v1/absence-requests` |
| Review absence requests | `GET /api/v1/sections/{id}/absence-requests` |
| Approve/reject absence | `PATCH /api/v1/absence-requests/{id}` |
| Load notifications | `GET /api/v1/notifications` |
| Student charts | `GET /api/v1/students/me/statistics` |
| Class charts | `GET /api/v1/sections/{id}/statistics` |

## Attendance UI behavior

1. Professor starts a session and receives `code`, `qr_token`, and
   `location_required`.
2. Display the code or render `qr_token` as a QR image. Do not store either in
   local storage.
3. If location is required, request browser/mobile coordinates and send
   `latitude` and `longitude` with the code or QR token.
4. Show success only for HTTP `200`.
5. Handle `400` invalid code, `403` not enrolled/outside radius, `409` already
   confirmed, and `410` expired session.

## Statistics charts

Student statistics:

- Progress/donut chart: `attendance_percentage`
- Status chart: `present`, `late`, `absent`
- Timeline: `by_session[].date` and `by_session[].status`

Class statistics:

- Overall progress: `attendance_percentage`
- Session chart: `by_session[].date` and
  `by_session[].attendance_percentage`
- Confirmation count: `by_session[].confirmed` versus `enrolled`

## Security requirements

- Prefer HTTP-only secure cookies for browser sessions; do not use
  `localStorage` for bearer tokens.
- Escape all user-provided text before rendering.
- Never log passwords, bearer tokens, codes, QR tokens, or exact locations.
- Do not expose one student's attendance or absence information to another.
- Replace development registration with institutional SSO or administrator
  provisioning before production.
