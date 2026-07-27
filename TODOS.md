# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the *code* delta needed to bring the
implementation in line with the current spec in `FEATURES.md` — plus
doc-vs-doc drift where two documents disagree about the same feature.

Delete entries once landed. Keep the file and this header even when empty.

---

## 1. `backend/README.md` contradicts `main.py` and the migration convention

- Claims "`create_all` replaced with `alembic upgrade head` in the
  lifespan". `main.py:28-30` runs **both** — `upgrade(…, "head")` *then*
  `Base.metadata.create_all` as a safety net. That's load-bearing (it is
  how a new table reaches a running dev DB), so the doc should describe it.
- "the initial migration captures all four current tables" — it now creates
  8.
- Refers to `alembic/versions/…_initial.py`; the file is
  `0001_initial_schema.py`.
- The **pre-alpha single-migration rule** (fold schema changes into `0001`
  rather than adding revisions) is documented nowhere, while the root
  README presents `just db-make-migrations` as the normal path. Two
  documents, opposite instructions.

## 2. `FEATURES.md` — small but real errors

- §2.9b: Explorer badge says "contribute a product to Open Food Facts,
  **see 2.7**". §2.7 is Internationalization; the OFF contribution is
  described in **§2.1**. Broken cross-reference.
- §3 Data Model has no `RewardTier` / `ProfileReward` entry, although
  §2.9c describes both tables in detail. Every other table is listed.
- §2.9 still reads "Achievements and unlocks land in WL-5.4 — this is
  their foundation". Achievements shipped (§2.9b describes them as live);
  only the unlock table is still pending.
- §2.9c omits that reward levels must be **≥ 2** (`RewardTierCreate`
  rejects level 1 — everyone starts there). §4's API table states it, the
  prose doesn't.

## 3. `ROADMAP.md` — stale status and unowned dependencies

- **WL-4.6's last bullet is unchecked** ("Unlocks the *Explorer*
  achievement — earned via WL-5.4") but the badge is granted in
  `routers/products.py:278` and WL-5.4 lists it as done. Two items, one
  feature, opposite marks. Should be `[x]`.
- **WL-3.4's "standardize other primitives as features land"** names
  WL-4.1 (Checkbox/AlertDialog), WL-4.2 (Date Picker/Tooltip) and WL-5.1
  (Tabs/Combobox) as the trigger points. All three are ✅ and shipped
  without the migration, so the trigger has passed with the item still
  open — re-scope it or repoint it at features that haven't landed.
- **The avatar compositor has no owning item.** WL-5.1 and `FEATURES.md`
  §2.9 both promise the SVG parts, the `layers: [{slot, part}]` key and the
  compositor "land with WL-5.4" (`schemas.py:188` says the same), but
  WL-5.4's checklist has no such bullet — only "achievements/levels unlock
  avatar equipment (`ProfileUnlock`)". Either add the compositor to WL-5.4
  or repoint the three references at WL-5.5 (the art pass).
- **"Cleared the List" badge has no reciprocal item.** WL-5.4 defers it to
  WL-7.1, but WL-7.1's checklist never mentions it — unlike WL-7.2, which
  explicitly owns both items deferred to it. It will be forgotten when the
  shopping list is built.
- **Status-mark convention is inconsistent.** WL-3.2 and WL-4.6 are marked
  `[x] ✅` while still carrying unchecked sub-bullets (component tests, OFF
  image upload, Explorer). Either the parent isn't done or the leftovers
  belong in the item that actually owns them (WL-6.5 already claims the
  WL-3.2 leftover).

## 4. `CONTAINER_ENGINE`'s default is described three different ways

Found while fixing item 1 — the container engine is documented
inconsistently across three files:

- `justfile:4` defaults it to **docker**, but the comment above `up:`
  (`justfile:170`) says "set `CONTAINER_ENGINE=docker` to use Docker
  instead of Podman" — i.e. it claims the default is podman.
- `.env.example` sets `CONTAINER_ENGINE=podman`, and the justfile has
  `set dotenv-load`, so anyone who follows the README's "copy
  `.env.example` to `.env`" instruction silently flips the default to
  podman.
- `README.md` tells you to set `CONTAINER_ENGINE=podman` for Podman, which
  is only true when no `.env` exists.

Pick one default, then make all three agree.
