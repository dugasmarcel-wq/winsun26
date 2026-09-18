from pathlib import Path
import re

path = Path("upstream/app/src/main/java/rocks/gorjan/gokixp/MainActivity.kt")
s = path.read_text()

# Replace only the permission callback arguments inside the two media-player
# constructors. Do not span across functions: showWinamp/showWmp and their window
# plumbing are still native launcher features used by Explorer and Desktop 2.
winamp_pattern = re.compile(
    r'(val\s+winampApp\s*=\s*rocks\.gorjan\.gokixp\.apps\.winamp\.WinampApp\(\s*'
    r'context\s*=\s*this,\s*)'
    r'onRequestPermissions\s*=\s*\{.*?\},\s*'
    r'hasAudioPermission\s*=\s*\{.*?\},\s*'
    r'(onShowRenameDialog\s*=)',
    re.S,
)
s, winamp_count = winamp_pattern.subn(
    r'\1onRequestPermissions = { },\n            hasAudioPermission = { false },\n            \2',
    s,
    count=1,
)

wmp_pattern = re.compile(
    r'(val\s+wmpApp\s*=\s*rocks\.gorjan\.gokixp\.apps\.wmp\.WmpApp\(\s*'
    r'context\s*=\s*this,\s*)'
    r'onRequestPermissions\s*=\s*\{.*?\},\s*'
    r'hasVideoPermission\s*=\s*\{.*?\},\s*'
    r'canRequestPermissions\s*=\s*\{.*?\},\s*'
    r'onShowPermissionNotification\s*=\s*\{.*?\},\s*'
    r'(fileToPlay\s*=)',
    re.S,
)
s, wmp_count = wmp_pattern.subn(
    r'\1onRequestPermissions = { },\n            hasVideoPermission = { false },\n            canRequestPermissions = { false },\n            onShowPermissionNotification = { },\n            \2',
    s,
    count=1,
)

if winamp_count != 1:
    raise SystemExit(f"Could not safely patch Winamp permission callbacks (count={winamp_count})")
if wmp_count != 1:
    raise SystemExit(f"Could not safely patch WMP permission callbacks (count={wmp_count})")

# Permission-result branches are unreachable after the callbacks above are disabled.
s = re.sub(
    r'\n\s*AUDIO_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*VIDEO_PERMISSION_REQUEST_CODE\s*->',
    '\n            VIDEO_PERMISSION_REQUEST_CODE ->',
    s,
    count=1,
    flags=re.S,
)
s = re.sub(
    r'\n\s*VIDEO_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*NOTIFICATION_PERMISSION_REQUEST_CODE\s*->',
    '\n            NOTIFICATION_PERMISSION_REQUEST_CODE ->',
    s,
    count=1,
    flags=re.S,
)

# If dormant compatibility helpers still contain an old permission constant,
# convert it to an app-private sentinel. This preserves their String-typed call
# sites but can never request an Android media/storage permission.
for permission in (
    "READ_EXTERNAL_STORAGE",
    "WRITE_EXTERNAL_STORAGE",
    "READ_MEDIA_AUDIO",
    "READ_MEDIA_VIDEO",
    "READ_MEDIA_IMAGES",
):
    s = s.replace(
        f"android.Manifest.permission.{permission}",
        '"winsung.retired.NO_MEDIA_STORAGE_ACCESS"',
    )
    s = s.replace(f"Manifest.permission.{permission}", '"winsung.retired.NO_MEDIA_STORAGE_ACCESS"')

# Keep the Explorer all-files settings flow intact. Media-player permission
# callbacks above stay disabled, but My Computer may request its own explicit
# all-files access when the user opens Explorer.

# Structural invariants: both native player entry points must survive this pass.
for required in (
    "private fun showWinampDialog",
    "private fun createAndShowWinampDialog",
    "fun openWmp",
    "private fun showWmpDialog",
    "private fun createAndShowWmpDialog",
    "val winampApp = rocks.gorjan.gokixp.apps.winamp.WinampApp",
    "val wmpApp = rocks.gorjan.gokixp.apps.wmp.WmpApp",
):
    if required not in s:
        raise SystemExit(f"Media cleanup damaged native player structure: missing {required}")

path.write_text(s)

for token in (
    "READ_EXTERNAL_STORAGE",
    "WRITE_EXTERNAL_STORAGE",
    "READ_MEDIA_AUDIO",
    "READ_MEDIA_VIDEO",
    "READ_MEDIA_IMAGES",
):
    if token in s:
        raise SystemExit(f"Legacy broad media/storage token still present in MainActivity: {token}")

print("Legacy Winamp/WMP media permission callbacks removed; Explorer storage flow preserved")
