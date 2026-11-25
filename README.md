# USA Softball Bat Checker (v2.0)

Check any bat's model number on your phone to make sure it is legal for MSSL / USA Softball play.

## Automatic Weekly Sync

A GitHub Actions workflow (`.github/workflows/sync-bats.yml`) runs every Saturday evening (`01:00 UTC` Sunday — 8:00 PM EST / 9:00 PM EDT) before Sunday games:

1. `python3 sync_bats.py` fetches the live Certified Bats HTML table (`equipmentdetail.asp`) and all three Non-Approved Bat List PDFs (`BB1P2000.asp`, `build_batlist_w_pics_2000.asp`, `build_batlist_w_pics_2004.asp`) directly from USA Softball.
2. `python3 verify_banned_bats.py` verifies all known banned bats remain flagged `BANNED`.
3. If the bat data changed, GitHub Actions commits and pushes the updated `bats.json` directly to `master`, automatically updating GitHub Pages.

To trigger an immediate sync manually, run `python3 sync_bats.py` locally or click **Run workflow** under **Actions → Weekly USA Softball Bat Sync** on GitHub.
