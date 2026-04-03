# CityPulse Architecture

## Roles

### Citizen

- Submits civic issues with text, media, and optional geolocation.
- Swipes or votes on nearby or relevant issues to improve prioritization signals.
- Tracks issue visibility, responses, and ticket progression.

### Admin

- Reviews incoming issues and moderation outcomes.
- Converts validated reports into operational tickets.
- Responds to citizens and manages issue lifecycle states.

## Core Entities

### `user`

- Identity and account record for both citizens and admins.
- Stores role, locale, and activation state.

### `issue`

- Primary report submitted by a citizen.
- Holds descriptive text, status, locale metadata, and optional spatial data.

### `issue_vote`

- Explicit vote or support signal tied to a user and an issue.
- Useful for ranking, prioritization, and public credibility signals.

### `swipe_feedback`

- Tinder-like directional feedback over issue cards.
- Supports relevance learning, personalization, and lightweight engagement.

### `moderation_result`

- Stores AI or human moderation outcomes for an issue.
- Designed for future content safety, spam detection, and policy review.

### `attachment`

- Metadata for uploaded images, video, or documents.
- Backed by an S3-compatible object storage interface.

### `ticket`

- Internal operational record created from an issue for government follow-up.
- Supports assignment, status tracking, and internal workflows.

### `admin_reply`

- Public or internal response authored by an admin.
- Allows direct feedback loops between government staff and citizens.

## High-Level Flow

### Issue Submission

1. A citizen submits an issue from the frontend with text, media references, and optional coordinates.
2. The frontend posts the payload to the backend API.
3. The backend validates the request, stores metadata, and persists the base issue record.
4. Attachment uploads are coordinated through the storage abstraction and linked back to the issue.

### Moderation

1. After persistence, the backend schedules an async moderation task placeholder.
2. The moderation layer evaluates content through future AI or policy services.
3. A `moderation_result` record is attached to the issue.
4. The issue status can then move into review, publication, or rejection states depending on policy.

### Admin Response

1. Admin-facing routes query moderated issues and related signals.
2. An admin can open a `ticket`, update issue status, or post an `admin_reply`.
3. Citizen-facing surfaces can later consume those status changes and responses.

## Design Principles

- Mobile-first interaction patterns with room for richer desktop workflows.
- Locale-aware routing and content primitives from the first scaffold.
- AI moderation and recommendation hooks are kept separate from transport and persistence layers.
- Admin and citizen experiences are separated by route groups, not separate products.
- Backend modules are split by API, core config, data layer, domain services, and async task boundaries.
