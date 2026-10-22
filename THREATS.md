\# THREATS.md



Status: CLOSED = fixed and tested, PARTIAL = some protection, NOT YET = not

built yet, ACCEPTED = I knowingly left it and say why.

Last updated: 2026-10-22 (end of build day 1; upload, grants and search are not built yet).



\## Access control



1\. A stranger reaches someone else's document - CLOSED (function level)

&#x20;  - Every document decision goes through authorize() in app/authz.py. It denies

&#x20;    by default.

&#x20;  - Tests: tests/test\_authz.py checks owner, read-grantee, edit-grantee,

&#x20;    stranger, other owner, admin and revoked user against read/edit/delete/share.

&#x20;  - NOT YET: the document routes that call authorize() are not built, so

&#x20;    this is only proven for the function, not for any endpoint.



2\. A stranger learns a document exists - CLOSED (function level)

&#x20;  - A refused request returns 404, the same as a missing document.

&#x20;  - Test: test\_denied\_is\_404 and test\_missing\_document\_is\_404.



3\. Revoked access keeps working - CLOSED (function level)

&#x20;  - A grant is never deleted; revoking sets revoked\_at, and authorize() reads

&#x20;    the database on every call, so there is no cache.

&#x20;  - Checked by removing the revoked\_at filter on purpose: 2 tests failed.

&#x20;  - NOT YET: sessions issued before a revoke are covered by token\_version

&#x20;    (below); download links do not exist yet.



4\. An invented action succeeds for the owner - CLOSED

&#x20;  - authorize() rejects any action outside KNOWN\_ACTIONS, even for the owner.

&#x20;  - Found by me while writing tests. Test: test\_unknown\_action\_is\_denied\_even\_for\_owner.



5\. Deleted document or deactivated user still gets access - CLOSED (function level)

&#x20;  - Tests: test\_deleted\_document\_is\_denied\_even\_for\_owner, test\_inactive\_user\_is\_denied.



6\. Admin reads document contents - ACCEPTED as a design choice

&#x20;  - Admins get no special access to files; they will see metadata and the audit

&#x20;    log only. Tested: admin is denied read/edit/delete/share on someone's document.



7\. A user sends role=admin or owner\_id in a request (mass assignment) - NOT YET

&#x20;  - There are no endpoints that create or edit users or documents yet.

&#x20;    The role always comes from the database, never from the token or request.



\## Sessions and login



8\. An old token works after logout - CLOSED

&#x20;  - The token holds a token\_version; every request reloads the user and compares

&#x20;    it. Logout bumps the version. Tested by hand: /me returned 401 after logout.

&#x20;  - NOT YET: no automated test for this yet.



9\. A deactivated or deleted user's token keeps working - PARTIAL

&#x20;  - Every request reloads the user and checks is\_active, so the token stops

&#x20;    working at once. Not covered by an automated test yet.



10\. Forged or "alg=none" token - PARTIAL

&#x20;   - The server only accepts HS256 signed with SECRET\_KEY, and tokens expire

&#x20;     after 8 hours. No dedicated test yet.



11\. Login reveals which emails exist - CLOSED

&#x20;   - Wrong email and wrong password return the same 401 message, and the password

&#x20;     check runs even for unknown emails so timing is similar. Tested by hand.



12\. Password guessing / brute force - NOT YET

&#x20;   - There is no rate limit or lockout. The users table has a failed\_logins

&#x20;     column, but it is not used yet. Planned for day 5.



13\. Password database leak - CLOSED

&#x20;   - Passwords are stored as argon2 hashes, never as plain text.



\## Secrets and operations



14\. A secret is committed to Git - PARTIAL

&#x20;   - My repo had no rule for .env. I found it with `git status` before

&#x20;     committing, added .env to .gitignore, and `git log -- .env` is empty.

&#x20;   - ACCEPTED RISK, TO FIX BEFORE DEPLOY: my database password and the first

&#x20;     SECRET\_KEY appeared in screenshots and in my chat with the AI tool. I will

&#x20;     replace both before the live deployment.



15\. Tests wipe real data - CLOSED

&#x20;   - Tests use a separate database (trustvault\_test) and conftest.py refuses to

&#x20;     run if the database name is not trustvault\_test.



\## Audit trail



16\. Denied attempts are not recorded - CLOSED (function level)

&#x20;   - authorize() writes a "denied" audit row for every refusal.

&#x20;   - Test: test\_denied\_attempt\_is\_audited.



17\. The audit log can be quietly changed - NOT YET

&#x20;   - Planned: hash chain, an INSERT-only database role, and a verify endpoint.

&#x20;   - Known limit that will remain: a database superuser could still rewrite it,

&#x20;     so the plan is to export the latest hash somewhere outside the database.



\## Not yet built, so not yet defended



\- Upload validation (file type, size, path traversal in names, SVG/HTML files)

\- Download through authorize(), safe response headers

\- Search that never reveals hidden documents

\- CSRF/CORS, rate limiting, security headers

\- AI sharing suggestion (must never grant access by itself)

