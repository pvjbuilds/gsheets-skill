# Setting up gsheets on a new machine

Two things have to be true before this works:

1. **The code is installed** — 30 seconds, one command.
2. **Google trusts this machine** — either copy your credentials across from a machine
   that already works (2 minutes), or create fresh ones (5 minutes).

Do Step 1, then pick **Path A** or **Path B** in Step 2. Step 3 confirms it worked.
**If you took Path B, read Step 4 as well** — otherwise the tool stops working after
a week and the reason is not obvious.

---

## Step 1 — Install the code

```bash
git clone https://github.com/pvjbuilds/gsheets-skill.git
cd gsheets-skill
./install.sh
```

Needs `git` and `python3` (any version 3.9+). On a fresh Mac, `xcode-select --install`
gets you both.

The installer:

- copies the backend to `~/.gsheets-mcp`
- creates a Python virtualenv there and installs `gspread`, `google-auth-oauthlib`, `mcp`
- copies the skill to `~/.claude/skills/gsheets/`
- runs the self-check — you should see `ok`

**It always installs to `~/.gsheets-mcp`, no matter where you cloned the repo.** That's
what makes the skill's paths work identically on every machine. Clone it to your
Desktop, to `~/code`, wherever — doesn't matter.

Re-running `install.sh` later is safe. It updates the code and leaves your credentials
and virtualenv alone.

---

## Step 2 — Google credentials

### Path A — copy from a machine that already works (easiest)

Everything Google needs lives in one folder. On the **old** machine:

```bash
open ~/.config/gspread
```

Copy both files (`credentials.json` and `authorized_user.json`) to the same folder on
the **new** machine:

```bash
mkdir -p ~/.config/gspread
# then drop the two files in — AirDrop, USB, or a password manager's secure notes
```

**Don't email them to yourself or put them in Dropbox/Drive.** `credentials.json` is
your OAuth client secret and `authorized_user.json` is a live token to your Google
account. Treat them like passwords.

That's it — no browser step. Skip to Step 3.

### Path B — create fresh credentials (no access to the old machine)

Do this once in your browser, signed in as **the Google account that owns your sheets**.

1. **Create a project** — https://console.cloud.google.com/projectcreate
   Any name. Wait for it to finish, then make sure it's selected in the top bar.

2. **Turn on the Sheets API** — https://console.cloud.google.com/apis/library/sheets.googleapis.com
   Click **Enable**.

3. **Set up the consent screen** — *APIs & Services → OAuth consent screen*
   - User type: **External**
   - App name: anything (`gsheets` is fine)
   - Support email + developer contact: your own address
   - Save, then go to **Audience → Test users → Add users** and add **your own Google
     address** — the one that owns the sheets. Miss this and you'll get "access denied"
     at the consent screen.

4. **Create the credential** — *APIs & Services → Credentials → Create credentials →
   OAuth client ID*
   - Application type: **Desktop app** ← this exact type matters
   - Create, then **Download JSON**

5. **Put it where the tool looks:**

   ```bash
   mkdir -p ~/.config/gspread
   mv ~/Downloads/client_secret_*.json ~/.config/gspread/credentials.json
   ```

   The filename must be exactly `credentials.json`.

6. **Authorise once** — this opens your browser:

   ```bash
   ~/.gsheets-mcp/.venv/bin/python ~/.gsheets-mcp/sheets.py create "gsheets setup test"
   ```

   Pick the sheet-owning Google account. You'll see **"Google hasn't verified this
   app"** — that's expected, the app is yours and unpublished. Click **Advanced →
   Go to (your app name)**, then **Continue**.

   It prints a URL for a new empty spreadsheet. Open it to confirm, then delete it.

Your token is now cached in `~/.config/gspread/authorized_user.json`. No browser again
on this machine.

**Now read Step 4.** As things stand, Google will sign you out again in seven days.

---

## Step 3 — Confirm it works

```bash
ls ~/.config/gspread/authorized_user.json          # exists = authorised
~/.gsheets-mcp/.venv/bin/python ~/.gsheets-mcp/test_sheets.py   # prints "ok"
```

Then open a **new** Claude session and ask it something real:

> "List the tabs in this sheet: `<paste a sheet URL>`"

If it comes back with your tab names, you're done.

---

## Step 4 — Stop it breaking after a week

**Only needed if you took Path B. Skip it and the tool will stop working every seven days.**

When you create a project in Google Cloud, Google files it under **"Testing"** — it assumes
you're still building something. To limit the damage a half-finished app can do, Google
deliberately cancels its sign-in after **seven days**.

Nothing warns you. Everything works fine, and then one morning every command fails with a
message about `invalid_grant` or a "Bad Request". Your data is untouched and the tool isn't
broken — Google has simply logged you out.

You have two ways to deal with it.

### Option 1 — live with it (no setup)

When it stops working, sign in again:

```bash
rm ~/.config/gspread/authorized_user.json
~/.gsheets-mcp/.venv/bin/python -c "import gspread; gspread.oauth(scopes=['https://www.googleapis.com/auth/spreadsheets'])"
```

A browser opens, you pick your account, and you're working again. Thirty seconds, about once
a week, indefinitely. Perfectly reasonable if you only use this occasionally.

### Option 2 — turn the expiry off for good (about 10 minutes, once)

Tell Google the app is finished rather than an experiment. Sign-ins then last indefinitely.

Google asks for a few things first: it won't call an app finished unless that app has a name,
a contact address, a home page and a privacy policy that people can actually visit. So you
need two web pages somewhere before you can proceed.

**Getting the two pages (free).** Put them in a **public** GitHub repository and switch on
GitHub Pages under *Settings → Pages*. Your addresses then look like
`https://yourname.github.io/yourrepo/`. This matters because Google won't accept an address
on a domain that isn't yours — and it treats `yourname.github.io` as yours.

There are two ready-made pages in this repo's `docs/` folder, a home page and a privacy
policy. Copy them, change the name and links, and they'll do the job.

**Then, in Google Cloud Console**, with your project selected:

1. In the left menu open **Google Auth Platform**. (Older guides call this section the
   "OAuth consent screen" — same thing, renamed.)
2. Go to **Branding** and fill in:

   | Field | What to put |
   |---|---|
   | App name | anything, e.g. `gsheets` |
   | User support email | your own address |
   | Authorized domains | `yourname.github.io` |
   | Application home page | `https://yourname.github.io/yourrepo/` |
   | Privacy policy link | `https://yourname.github.io/yourrepo/privacy.html` |
   | Terms of service | leave blank, it's optional |

   **Add the authorized domain before you paste the two addresses** — the address fields
   reject anything from a domain you haven't listed yet.

3. Save, then open **Audience** and click **PUBLISH APP → Confirm**.

The status changes to "In production" and the seven-day clock is gone. Your existing sign-in
keeps working — you don't have to authorise again.

**One thing to ignore:** afterwards Google may show a prompt about *verification*, sometimes
with a "Prepare for verification" button. Don't click it. Verification only applies to apps
that strangers will sign into. You're the only user of yours, so you never need to submit
anything. You will still see a **"Google hasn't verified this app"** screen on the rare
occasion you sign in again — click **Advanced → Go to (your app)**. It's cosmetic, not a
failure.

---

## When something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| `invalid_grant` / "Bad Request", after it had been working fine | Google cancelled the sign-in because the project is still in "Testing" mode | Sign in again (Step 4, Option 1) — then do Step 4, Option 2 so it stops recurring |
| Claude says it can't find the skill | Session started before install | Restart the session |
| Claude says it has no shell access | Session runs in a cloud sandbox, not on this machine | Use a session with terminal access |
| `FileNotFoundError: credentials.json` | Step 2 not done | Path A or Path B above |
| `403 ... has not been used in project` | Sheets API not enabled | Step 2, Path B, item 2 |
| `access_denied` at the consent screen | Your address isn't a test user | Step 2, Path B, item 3 |
| `403 The caller does not have permission` | Signed in as the wrong Google account | Delete `~/.config/gspread/authorized_user.json` and re-authorise as the sheet owner |
| `SpreadsheetNotFound` | Wrong ID, or that account doesn't own the sheet | The ID is the part of the URL between `/d/` and `/edit` |
| `APIError: 429` | Google rate limit | Wait a minute; batch your writes |

**Start over cleanly:**

```bash
rm ~/.config/gspread/authorized_user.json    # re-authorise, keeps your OAuth client
rm -rf ~/.gsheets-mcp                        # then re-run ./install.sh
```

Deleting `authorized_user.json` only signs this machine out. It doesn't touch your
sheets or your Google account.

---

## What you should know about safety

- The tool has the **`spreadsheets` scope only** — it cannot see your Drive, your Gmail,
  or anything else. It reaches spreadsheets you explicitly hand it, by ID.
- **It has no delete capability.** Nothing in the code can remove a file or a row.
- The skill won't restructure a sheet on its own initiative, and it reads back and
  reports every change it makes.
- **Never commit `~/.config/gspread/` to git.** This repo's `.gitignore` blocks `*.json`
  as a backstop, but the folder lives outside the repo — just don't move it in.
