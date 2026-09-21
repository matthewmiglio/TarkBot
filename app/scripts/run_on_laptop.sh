#!/usr/bin/env bash
# Run one of this repo's live tests on the Windows laptop over Tailscale, and print its output.
#
#   scripts/run_on_laptop.sh tests/hideout_craft_actions/test_bitcoin_farm_live.py --dry
#   scripts/run_on_laptop.sh tests/hideout_craft_actions/test_bitcoin_farm_live.py
#
# Run it from app/. The laptop needs Tarkov already up; this does not launch it.
#
# WHY IT IS NOT JUST `ssh laptop python ...`
# An SSH process on Windows has no desktop. Every screen grab in one fails outright ("screen grab
# failed" out of Pillow, not a black image) and every click goes nowhere, so a live test run that
# way cannot see the game at all. A scheduled task created /RU <user> /IT runs inside that user's
# logged-on interactive session, which does have a desktop. So the work is handed to a task, and
# this script is the thing that hands it over and reads the answer back.
#
# The task's own console window is hidden by run_live.cmd before anything reads the screen: the
# game runs borderless full-screen, so a console on top of it is a hole in every match. The first
# run of this found the hideout tab at 0.526 with that window over the left half of the menu.
#
# Three steps: sync the code, run the task, print the log. The sync is a tarball of the python and
# the reference crops only, without tests/output (921MB of saved frames) or build/ and dist/.
set -euo pipefail

HOST=laptop
REMOTE='C:/Users/matmi/tarkbot'
REMOTE_WIN='C:\Users\matmi\tarkbot'
TASK=tarkbot-live
APP="$(cd "$(dirname "$0")/.." && pwd)"
TEST=${1:?usage: run_on_laptop.sh <test path relative to app/> [test args...]}
shift

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "== syncing $APP -> $HOST:$REMOTE"
tar -czf "$TMP/app.tgz" --exclude='__pycache__' --exclude='*.pyc' -C "$APP" \
    $(cd "$APP" && ls *.py) requirements.txt interact gui game_client "$TEST"
ssh "$HOST" "if not exist $REMOTE_WIN mkdir $REMOTE_WIN" >/dev/null
scp -q "$TMP/app.tgz" "$HOST:$REMOTE/app.tgz"
scp -q "$APP/scripts/run_live.cmd" "$HOST:$REMOTE/run_live.cmd"
ssh "$HOST" "cd /d $REMOTE_WIN && tar -xzf app.tgz" >/dev/null

# The test's own flags go in a file, not on the task's command line: quoting them through
# ssh -> cmd.exe -> schtasks /tr is a thicket, and run_live.cmd reads the file. The test path too,
# so one task serves every live test rather than one task per test.
printf '%s' "$TEST" > "$TMP/run_test.txt"
printf '%s' "$*" > "$TMP/run_args.txt"
scp -q "$TMP/run_test.txt" "$TMP/run_args.txt" "$HOST:$REMOTE/"

echo "== running $TEST $* in the laptop's desktop session"
ssh "$HOST" "del $REMOTE_WIN\\live.log 2>nul & schtasks /create /f /tn $TASK /tr \"$REMOTE_WIN\\run_live.cmd\" /sc once /st 00:00 /ru matmi /it" >/dev/null
ssh "$HOST" "schtasks /run /tn $TASK" >/dev/null

# schtasks /run returns the moment the task is launched, so poll the task's own state rather than
# guessing how long a carousel sweep takes. Status goes back to Ready when the task has finished.
for _ in $(seq 1 120); do
    sleep 5
    if ssh "$HOST" "schtasks /query /tn $TASK /fo list" | grep -qi 'Status: *Ready'; then
        break
    fi
    echo "   still running..."
done

echo "== log"
ssh "$HOST" "type $REMOTE_WIN\\live.log"
