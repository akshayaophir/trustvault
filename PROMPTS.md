\# PROMPTS.md



How I used AI: I used Claude in the chat window as a guide while building

TrustVault. I pasted its code into my project, ran it, and checked it with

`git status`, pytest and my own reading. I did not use a coding agent, so I have

no reused context file. Entries are dated and link to the commit that fixed

the problem.



\## 2026-10-20: .env was not hidden by .gitignore

\- Asked: how to keep database passwords and keys out of Git.

\- Produced: advice that the Python .gitignore template would hide `.env`.

\- Wrong: my repo had no such rule. `git status` listed `.env` as untracked, and

&#x20; a `git add .` would have pushed my database password to GitHub.

\- Did instead: added `.env` to .gitignore, and now name files in `git add` and

&#x20; check `git status` before every commit. Fixed in e61fa79.



\## 2026-10-20: Wrong PostgreSQL driver

\- Asked: to connect the app to PostgreSQL.

\- Produced: instructions that installed psycopg2.

\- Wrong: the SQLAlchemy version I had expected psycopg (version 3), so the first

&#x20; test failed with "No module named psycopg".

\- Did instead: installed `psycopg\[binary]` and re-ran. Fixed in e61fa79.



\## 2026-10-20: Python cache files got committed

\- Produced: a `git add` that staged `\_\_pycache\_\_/\*.pyc` files.

\- Wrong: generated files do not belong in the repository.

\- Did instead: `git rm -r --cached app/\_\_pycache\_\_` and added the ignore rules.

&#x20; Fixed in dd6a45a.



\## 2026-10-22: authorize() allowed unknown actions for the owner (access control)

\- Asked: for one central authorize() function that denies by default.

\- Produced: a function where the owner check ran before the check that the

&#x20; action is valid. An owner would have been allowed any invented action such

&#x20; as "teleport", which breaks deny-by-default.

\- Wrong: noticed while planning the tests. I wrote

&#x20; test\_unknown\_action\_is\_denied\_even\_for\_owner, which failed on the first

&#x20; version.

\- Did instead: added a KNOWN\_ACTIONS check at the top of is\_allowed().

&#x20; Fixed in 483f19c.



\## 2026-10-22: Checking that the tests really test revocation (access control)

\- What I did: temporarily deleted the `Grant.revoked\_at.is\_(None)` filter from

&#x20; is\_allowed() and ran the revocation tests.

\- Result: 2 tests failed with "DID NOT RAISE HTTPException"

&#x20; (revoked-read and revoking\_takes\_effect\_immediately). Only the read case failed

&#x20; because the revoked grant was a read grant, so edit/delete/share were still

&#x20; denied by other rules.

\- Did instead: restored the line with `git restore`; tests passed again.

\- Lesson: a green test suite does not prove the tests work. Breaking the code on

&#x20; purpose does.

