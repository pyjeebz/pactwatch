# consumer-mobile

Mobile application that consumes the User API.

## Endpoints Used

| Method | Path | Usage |
|--------|------|-------|
| GET | /users/{id} | User profile screen |
| POST | /users | Registration flow |
| GET | /users/{id}/orders | Order history screen |

## What would break us

- Removing or changing fields on the `User` schema (we parse `id`, `name`, `email`)
- Removing the orders endpoint
- Changing the order status enum (we render status badges)
