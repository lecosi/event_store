# Screens

Reserved space for screenshots of the application. The images are added later; until then
each section holds a plain-text placeholder. The interface text of the app is in Spanish.

## How to add an image

1. Take the screenshot (a desktop width of about 1280 px for pages, about 390 px for the
   mobile ones) and save it as PNG in `docs/images/` using the file name shown in the
   placeholder of the section, for example `docs/images/event-list.png`.
2. In this file, replace the whole `Screenshot pending` block of that section with:

   ```markdown
   ![Event list with search and pagination](images/event-list.png)
   ```

3. Keep the alt text short and descriptive. Do not add an image link before the file
   exists, so there are no broken images.
4. Do not include real personal data: use the demo seed (see
   [backend-operations.md](backend-operations.md#seeding)).

## Index

| Screen | Route | Image file |
| --- | --- | --- |
| [Login](#login) | `/login` | `docs/images/login.png` |
| [Register](#register) | `/register` | `docs/images/register.png` |
| [Event list](#event-list) | `/` | `docs/images/event-list.png` |
| [Event detail](#event-detail) | `/events/:id` | `docs/images/event-detail.png` |
| [Event detail, management view](#event-detail-management-view) | `/events/:id` | `docs/images/event-detail-manage.png` |
| [Event form](#event-form) | `/events/new` and `/events/:id/edit` | `docs/images/event-form.png` |
| [Speaker form](#speaker-form) | `/speakers/new` | `docs/images/speaker-form.png` |
| [My events](#my-events) | `/profile` | `docs/images/profile.png` |
| [Reports](#reports) | `/reports` | `docs/images/reports.png` |
| [Admin users](#admin-users) | `/admin/users` | `docs/images/admin-users.png` |
| [Not found](#not-found) | any unknown path (`*`) | `docs/images/not-found.png` |
| [Navbar, anonymous](#navbar-anonymous) | all pages | `docs/images/navbar-anonymous.png` |
| [Navbar, organizer](#navbar-organizer) | all pages | `docs/images/navbar-organizer.png` |
| [Mobile: event list](#mobile-event-list) | `/` at phone width | `docs/images/mobile-event-list.png` |
| [Mobile: event detail](#mobile-event-detail) | `/events/:id` at phone width | `docs/images/mobile-event-detail.png` |

## Login

**Route:** `/login`

Email and password form. Public. After signing in it returns the user to the page they came from.

> **Screenshot pending:** save the image as `docs/images/login.png` and replace this block with `![Login](images/login.png)`.

## Register

**Route:** `/register`

Account creation form (name, email, password and confirmation). Public. New accounts get the organizer role.

> **Screenshot pending:** save the image as `docs/images/register.png` and replace this block with `![Register](images/register.png)`.

## Event list

**Route:** `/`

Searchable, paginated grid of event cards (9 per page) with a status badge. Public; organizers and admins also see non-published events according to their role.

> **Screenshot pending:** save the image as `docs/images/event-list.png` and replace this block with `![Event list](images/event-list.png)`.

## Event detail

**Route:** `/events/:id`

Event information, status badge, seats left, the register/cancel button and the session list with per-session enrollment. Public to read; registering and enrolling need a login.

> **Screenshot pending:** save the image as `docs/images/event-detail.png` and replace this block with `![Event detail](images/event-detail.png)`.

## Event detail, management view

**Route:** `/events/:id`

The same page for the event's organizer or an admin: edit link, status change, participants CSV download, delete, and the add/edit/delete session controls.

> **Screenshot pending:** save the image as `docs/images/event-detail-manage.png` and replace this block with `![Event detail, management view](images/event-detail-manage.png)`.

## Event form

**Route:** `/events/new` and `/events/:id/edit`

Create or edit an event (name, description, location, dates, capacity). Organizers and admins; editing is limited to the event's organizer or an admin, and only while the event is not cancelled or finished.

> **Screenshot pending:** save the image as `docs/images/event-form.png` and replace this block with `![Event form](images/event-form.png)`.

## Speaker form

**Route:** `/speakers/new`

Add a speaker (name, bio, optional email) to the shared directory. Organizers and admins.

> **Screenshot pending:** save the image as `docs/images/speaker-form.png` and replace this block with `![Speaker form](images/speaker-form.png)`.

## My events

**Route:** `/profile`

The logged-in user's profile summary and the events they are registered to, with a cancel action. Any logged-in user.

> **Screenshot pending:** save the image as `docs/images/profile.png` and replace this block with `![My events](images/profile.png)`.

## Reports

**Route:** `/reports`

Participants preview by event or by session with search, status and date filters, pagination and CSV download. Organizers (own events) and admins; other roles see a not-allowed message.

> **Screenshot pending:** save the image as `docs/images/reports.png` and replace this block with `![Reports](images/reports.png)`.

## Admin users

**Route:** `/admin/users`

Email-prefix search over user accounts with inline editing of name, email, role and active flag. Admins only; other roles see a not-allowed message.

> **Screenshot pending:** save the image as `docs/images/admin-users.png` and replace this block with `![Admin users](images/admin-users.png)`.

## Not found

**Route:** any unknown path (`*`)

Message and link back to the home page. Public.

> **Screenshot pending:** save the image as `docs/images/not-found.png` and replace this block with `![Not found](images/not-found.png)`.

## Navbar, anonymous

**Route:** all pages

Brand link plus Login and Register links. Shown to visitors without a session.

> **Screenshot pending:** save the image as `docs/images/navbar-anonymous.png` and replace this block with `![Navbar, anonymous](images/navbar-anonymous.png)`.

## Navbar, organizer

**Route:** all pages

Shows New event, New speaker, Reports and My events, the user name and Logout. Admins also see Administration.

> **Screenshot pending:** save the image as `docs/images/navbar-organizer.png` and replace this block with `![Navbar, organizer](images/navbar-organizer.png)`.

## Mobile: event list

**Route:** `/` at phone width

The event list below the 640 px breakpoint, where the navbar stacks vertically and the grid becomes a single column.

> **Screenshot pending:** save the image as `docs/images/mobile-event-list.png` and replace this block with `![Mobile: event list](images/mobile-event-list.png)`.

## Mobile: event detail

**Route:** `/events/:id` at phone width

The event detail and session list at phone width.

> **Screenshot pending:** save the image as `docs/images/mobile-event-detail.png` and replace this block with `![Mobile: event detail](images/mobile-event-detail.png)`.
