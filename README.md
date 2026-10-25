
# TrustVault

Secure document sharing where the wrong person cannot read a file, and you can prove who did.

**Live site:** https://trustvault-3dac.onrender.com
The free host sleeps when idle, so the first load can take up to a minute.
**API reference (interactive):** https://trustvault-3dac.onrender.com/docs

## Demo accounts

Password for all four: `<DEMO PASSWORD>`

| Role | Email | What it can do |
|---|---|---|
| Admin | admin@trustvault.test | Sees all activity, permission changes and alerts; disables accounts; checks the audit log's integrity. Cannot open other people's documents. |
| Owner | owner1@trustvault.test | Uploads, shares, takes access back, edits and deletes their own documents. Has two sample documents. |
| Owner | owner2@trustvault.test | A second owner with no documents, to try cross-user access. |
| Viewer | viewer@trustvault.test | Opens only what has been shared with them. |

## Try it in three minutes

1. Sign in as **owner1**, open **Documents**, click the share icon on a document and give **viewer** access.
2. In a private window, sign in as **viewer** and download that document. It works.
3. Back as owner1, click **Take back**. In the viewer window, press download again: the viewer is refused on the very next request, without signing in again.
4. Sign in as **owner2**. The list is empty, and searching finds nothing from owner1.
5. Sign in as **admin** and open **Activity** (every action, including the refused ones), **Alerts**, **Users** and **Integrity** (checks that no past entry was changed).

## How access works

- Every document has one **owner** and per-person **grants** (`read` or `edit`) given by the owner. A grant is never deleted; taking access back marks it revoked.
- One function, `authorize()` in `app/authz.py`, decides every document access. It denies by default. Every document and grant route calls it first.
- A refusal returns **404**, the same as a missing document, so nobody can tell whether a hidden document exists.
- The login token only says who you are. What you may open is read from the database on every request, so revoking access, disabling an account or logging out takes effect on the very next request.
- Admins manage accounts and the audit trail. They get no special access to document contents.
- Every attempt, allowed or refused, is written to an audit log. Each entry is chained to the previous one with a SHA-256 hash, and a database trigger refuses to update or delete rows.

## What is built

- Roles: admin, owner, viewer
- Upload with validation: allowed types are PDF, PNG, JPG and TXT, up to 5 MB, the real file content is checked, and file names are cleaned
- Download (as an attachment), list, rename and category edit, replace file contents (same file type only), delete (soft)
- Share and take back access (read or edit)
- Search by name, owner, category and date, filtered by permission inside the database query
- Audit trail of logins, uploads, downloads, edits, deletions and permission changes, including refused attempts
- Admin pages: activity with filters, permission changes, alerts (many refusals, bulk downloads), users (disable and enable accounts), audit integrity check
- Login protection: 5 failed attempts in 15 minutes lock that email for the rest of the window (HTTP 429)
- Security headers on every response; a strict Content-Security-Policy on the web page
- A web interface (no framework), plus the interactive API page at `/docs`

## What I did not build

- The AI sharing suggestion from the brief
- File versions and history (replacing contents overwrites the old file)
- Folders, groups, and sharing with people outside the company
- Retention or purge of deleted documents, and backups
- Per-IP rate limiting, antivirus scanning, ownership transfer

See `THREATS.md` for what I defended, what I tested and what I knowingly left open, and `PROMPTS.md` for how I used AI and where it was wrong.

## API: who may call each endpoint

401 = not signed in. 403 = wrong role. 404 = no access, or it does not exist (deliberately the same). 413 = file too large. 422 = bad input. 429 = account locked after repeated failed logins.

| Endpoint | Who may call it |
|---|---|
| GET `/` , GET `/health` , GET `/docs` | Anyone |
| POST `/auth/login` | Anyone (an email locks after 5 failures in 15 minutes) |
| POST `/auth/logout` , GET `/me` | Any signed-in user |
| POST `/documents` | Owners only |
| GET `/documents` | Any signed-in user; returns only documents they own or hold an active grant for. Filters: `q`, `owner`, `category`, `created_from`, `created_to` |
| GET `/documents/{id}` , GET `/documents/{id}/download` | The owner, or anyone with an active read or edit grant |
| PATCH `/documents/{id}` , PUT `/documents/{id}/content` | The owner, or anyone with an active edit grant |
| DELETE `/documents/{id}` | The owner only |
| POST, GET `/documents/{id}/grants` ; DELETE `/documents/{id}/grants/{user_id}` | The document's owner only |
| GET `/admin/audit` , `/admin/permission-changes` , `/admin/alerts` , `/admin/users` , `/admin/audit/verify` | Admins only |
| POST `/admin/users/{id}/deactivate` , `/admin/users/{id}/activate` | Admins only (not on yourself) |

Every document and grant route calls `authorize()` first, and every refusal is recorded in the audit log.

## Run it yourself

You need Python 3.11 or newer and a PostgreSQL database (I used Neon). Create a second, empty database named `trustvault_test` on the same server for the tests.

```
git clone https://github.com/akshayaophir/trustvault.git
cd trustvault
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL` and a long random `SECRET_KEY` (make one with `python -c "import secrets; print(secrets.token_hex(32))"`). Then:

```
python -m scripts.create_tables
python -m scripts.protect_audit
python -m scripts.seed
python -m scripts.seed_demo
uvicorn app.main:app --reload
```

`seed` asks for a password (12 characters or more) for the four demo users. `protect_audit` makes the audit table refuse updates and deletes. Open http://127.0.0.1:8000/.
`schema.sql` is the table definition, generated by `python -m scripts.export_schema`. If you ever need to change the demo passwords, run `python -m scripts.reset_passwords`.

## Tests

```
pytest -q
```

The tests use the `trustvault_test` database on the same server and refuse to run against any other database. They cover: every document route as the owner, a reader, an editor, a stranger, another owner, an admin and an anonymous caller; grant and revoke taking effect on the next request; upload validation; search never revealing hidden documents; the admin routes; audit chain tampering and the append-only table; login lockout; and forged or stale tokens.

## Deploy (Render)

A web service from this repository. Build command: `pip install -r requirements.txt`. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Environment variables: `DATABASE_URL`, `SECRET_KEY` (different from development), `PYTHON_VERSION=3.13.7`. After the first deploy, run `python -m scripts.create_tables` and `python -m scripts.protect_audit` once against the database.

## Layout

```
app/main.py            routes for login, health, security headers
app/authz.py           the one function that decides document access
app/audit.py           hash-chained audit log
app/routes/            documents, grants and admin routes
app/uploads.py         upload validation
app/static/            the web interface
scripts/               setup, seed and maintenance scripts
tests/                 automated tests
```
