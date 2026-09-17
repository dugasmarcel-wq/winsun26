from pathlib import Path
import re

path = Path("upstream/app/src/main/java/rocks/gorjan/gokixp/MainActivity.kt")
s = path.read_text()

# Winamp/WMP's inherited MediaStore library browsers asked for broad media/storage
# permissions. WINSUNG's requested media surface is the active Android media session
# bridge plus explicit document pickers, so these legacy permission callbacks are disabled.

def replace_permission_pair(text: str, permission_name: str) -> tuple[str, int]:
    pattern = re.compile(
        rf'onRequestPermissions\s*=\s*\{{.*?\}},\s*'
        rf'{re.escape(permission_name)}\s*=\s*\{{.*?\}},',
        re.S,
    )
    replacement = f'onRequestPermissions = {{ }},\n            {permission_name} = {{ false }},'
    return pattern.subn(replacement, text, count=1)

s, audio_count = replace_permission_pair(s, "hasAudioPermission")
s, video_count = replace_permission_pair(s, "hasVideoPermission")

if audio_count != 1:
    raise SystemExit(f"Could not replace Winamp audio permission callbacks (count={audio_count})")
if video_count != 1:
    raise SystemExit(f"Could not replace WMP video permission callbacks (count={video_count})")

# These result branches are now unreachable and should not imply WINSUNG requests them.
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

path.write_text(s)

for token in (
    "READ_EXTERNAL_STORAGE",
    "WRITE_EXTERNAL_STORAGE",
    "READ_MEDIA_AUDIO",
    "READ_MEDIA_VIDEO",
    "READ_MEDIA_IMAGES",
    "MANAGE_EXTERNAL_STORAGE",
    "ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION",
    "isExternalStorageManager",
):
    if token in s:
        raise SystemExit(f"Legacy broad media/storage token still present in MainActivity: {token}")

print("Legacy Winamp/WMP broad media permission callbacks removed")
