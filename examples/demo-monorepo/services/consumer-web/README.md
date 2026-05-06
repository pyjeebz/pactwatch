# consumer-web

Web dashboard that consumes the User API.

## Endpoints Used

| Method | Path | Usage |
|--------|------|-------|
| GET | /users/{id} | User detail page |
| GET | /users | User list page |
| GET | /admin/* | Admin panel (settings, user management) |

## What would break us

- Removing or changing fields on the `User` schema (we render user tables)
- Removing any admin endpoints (the admin panel depends on the full /admin/* subtree)
