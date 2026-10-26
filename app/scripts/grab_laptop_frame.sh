#!/usr/bin/env bash
# Take a full-screen screenshot of the laptop right now and copy it here.
#
#   scripts/grab_laptop_frame.sh            -> C:/tmp/tarkbot_frames/live-<time>.png
#   scripts/grab_laptop_frame.sh out.png    -> out.png
#
# Same trick as run_on_laptop.sh: an SSH process has no desktop, so the grab runs as a scheduled
# task in matmi's logged-on session. conhost --headless gives powershell no window at all, so
# nothing flashes over the game mid-run.
#
#   scripts/grab_laptop_frame.sh --pc [out.png]   -> this machine's 2560x1440 monitor instead
set -euo pipefail

if [ "${1:-}" = --pc ]; then
    OUT=${2:-C:/tmp/tarkbot_frames/pc-$(date +%Y%m%d-%H%M%S).png}
    mkdir -p "$(dirname "$OUT")"
    # Picked by size rather than by index, since the monitor order is not stable.
    python -c "import mss,mss.tools,sys; s=mss.MSS(); m=next(m for m in s.monitors[1:] if (m['width'],m['height'])==(2560,1440)); i=s.grab(m); mss.tools.to_png(i.rgb,i.size,output=sys.argv[1])" "$OUT"
    echo "$OUT"
    exit 0
fi

HOST=laptop
REMOTE='C:/Users/matmi/tarkbot'
REMOTE_WIN='C:\Users\matmi\tarkbot'
TASK=tarkbot-grab
OUT=${1:-C:/tmp/tarkbot_frames/live-$(date +%Y%m%d-%H%M%S).png}
mkdir -p "$(dirname "$OUT")"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Saved to .tmp then renamed, so the poll below never copies a half-written png.
cat > "$TMP/grab.ps1" <<'PS'
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type 'using System.Runtime.InteropServices; public class Dpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }'
[Dpi]::SetProcessDPIAware() | Out-Null
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
$bmp.Save("$PSScriptRoot\grab.tmp", [System.Drawing.Imaging.ImageFormat]::Png)
Move-Item -Force "$PSScriptRoot\grab.tmp" "$PSScriptRoot\grab.png"
PS

# Parentheses, because cmd reads everything after an unbracketed `if` as its body: written as
# `if not exist X mkdir X & del ...` the del only ran when the folder was missing, so the poll
# below copied the last run's grab.png before the task had written a new one.
ssh "$HOST" "(if not exist $REMOTE_WIN mkdir $REMOTE_WIN) & del $REMOTE_WIN\\grab.png 2>nul" >/dev/null
scp -q "$TMP/grab.ps1" "$HOST:$REMOTE/grab.ps1"
ssh "$HOST" "schtasks /create /f /tn $TASK /tr \"conhost.exe --headless powershell -NoProfile -ExecutionPolicy Bypass -File $REMOTE_WIN\\grab.ps1\" /sc once /st 00:00 /ru matmi /it && schtasks /run /tn $TASK" >/dev/null

for _ in $(seq 1 30); do
    if scp -q "$HOST:$REMOTE/grab.png" "$OUT" 2>/dev/null; then
        echo "$OUT"
        exit 0
    fi
    sleep 1
done
echo "no frame after 30s: is matmi logged on to the laptop?" >&2
exit 1
