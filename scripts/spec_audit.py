from pathlib import Path
import re

root = Path("upstream/app/src/main")
text_files = []
for suffix in ("*.kt", "*.java", "*.xml", "*.gradle", "*.properties"):
    text_files.extend(root.rglob(suffix))

corpus = {}
for path in text_files:
    try:
        corpus[path] = path.read_text(errors="ignore")
    except OSError:
        pass

controller_path = root / "java/rocks/gorjan/gokixp/winsung/Winsung98Controller.kt"
theme_path = root / "java/rocks/gorjan/gokixp/theme/ThemeManager.kt"
controller_text = controller_path.read_text(errors="ignore") if controller_path.exists() else ""
controller_upper = controller_text.upper()
theme_text = theme_path.read_text(errors="ignore") if theme_path.exists() else ""

checks = {
    "Quick Glance page": ["Quick Glance", "QuickGlance"],
    "GDELT live news": ["api.gdeltproject.org"],
    "Google News source": ["Google News"],
    "Reuters source": ["Reuters"],
    "AP source": ["Associated Press", '"AP"'],
    "AOL branding/pages": ["AOL"],
    "Samsung Phone target": ["com.samsung.android.dialer"],
    "Google Phone fallback": ["com.google.android.dialer"],
    "Signal target": ["org.thoughtcrime.securesms"],
    "Firefox target": ["org.mozilla.firefox"],
    "WhatsApp target": ["com.whatsapp"],
    "YouTube Music target": ["com.google.android.apps.youtube.music"],
    "Notification listener": ["NotificationListenerService", "BIND_NOTIFICATION_LISTENER_SERVICE"],
    "Media sessions": ["MediaSessionManager", "getActiveSessions", "MediaController"],
    "Scoped file picker": ["ACTION_OPEN_DOCUMENT", "ACTION_GET_CONTENT", "ActivityResultContracts.OpenDocument"],
    "Safe dialer intent": ["ACTION_DIAL"],
    "Windows 98 identity": ["Windows 98"],
    "Windows XP": ["Windows XP"],
    "Windows Vista": ["Windows Vista"],
    "Windows 7": ["Windows 7"],
    "Win7 independent icon prefs": ["custom_icons_windows7"],
    "Native Win98 bevel UI": ["ClassicBevelDrawable"],
    "Native AOL backdrop": ["AolBackdrop"],
    "Native AOL channel controls": ["AolChannelView"],
    "Taskbar-integrated fixed apps": ["R.id.taskbar_empty_space"],
    "Live notification badge refresh": ["badgeTick"],
    "Native Phone icon asset": ["custom_icons_98/Phone.webp"],
    "Native WhatsApp icon asset": ["custom_icons_98/WhatsApp.webp"],
    "Native YouTube icon asset": ["custom_icons_programs/YouTube.webp"],
}

aol_checks = {
    "AOL Today's News": "TODAY'S NEWS",
    "AOL Weather": "WEATHER",
    "AOL Internet": "INTERNET",
    "AOL Chat": "CHAT",
    "AOL Finance": "FINANCE",
    "AOL Games": "GAMES",
    "AOL Computing": "COMPUTING",
    "AOL Travel": "TRAVEL",
}

print("=== WINSUNG MASTER SPEC SOURCE AUDIT ===")
missing = []
for label, needles in checks.items():
    hit = None
    for path, text in corpus.items():
        for needle in needles:
            if needle in text:
                line = text[:text.index(needle)].count("\n") + 1
                hit = f"{path.relative_to(root)}:{line} [{needle}]"
                break
        if hit:
            break
    if hit:
        print(f"PASS | {label:<34} | {hit}")
    else:
        print(f"MISS | {label}")
        missing.append(label)

for label, needle in aol_checks.items():
    if needle in controller_upper:
        line = controller_upper[:controller_upper.index(needle)].count("\n") + 1
        print(f"PASS | {label:<34} | winsung/Winsung98Controller.kt:{line} [{needle}]")
    else:
        print(f"MISS | {label}")
        missing.append(label)

# The public selector must be exactly four environments. WindowsClassic is an
# internal compatibility object only; it is displayed and persisted as Windows 98.
selector = re.search(r'fun\s+all\(\)\s*:\s*List<AppTheme>\s*=\s*listOf\(([^)]*)\)', theme_text)
expected_selector = "WindowsClassic, WindowsXP, WindowsVista, Windows7"
if not selector or re.sub(r'\s+', '', selector.group(1)) != re.sub(r'\s+', '', expected_selector):
    print("MISS | exact four-environment selector")
    missing.append("exact four-environment selector")
else:
    print("PASS | exact four-environment selector    | Windows 98 / XP / Vista / 7")

classic_object = re.search(r'object\s+WindowsClassic\s*:\s*AppTheme\(\)\s*\{(.*?)\n\s*\}', theme_text, re.S)
if not classic_object or 'toString() = "Windows 98"' not in classic_object.group(1):
    print("MISS | WindowsClassic user-facing name is not Windows 98")
    missing.append("Windows 98 display identity")
else:
    print("PASS | WindowsClassic compatibility object displays only Windows 98")

if 'fun getAllPlus95Themes(): List<Plus95Theme> = emptyList()' not in theme_text:
    print("MISS | legacy Plus/95 theme choices are still exposed")
    missing.append("remove legacy 95/2000 clutter")
else:
    print("PASS | legacy Plus/95 theme choices hidden")

forbidden = {
    "QUERY_ALL_PACKAGES": "broad installed-app visibility",
    "MANAGE_EXTERNAL_STORAGE": "broad storage access",
    "READ_EXTERNAL_STORAGE": "legacy broad storage read",
    "ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION": "all-files settings request",
    "isExternalStorageManager": "all-files storage API",
    "READ_CONTACTS": "contacts access",
    "ContactsContract": "contacts database access",
    "CALL_PHONE": "direct calling permission",
    "ACTION_CALL": "direct phone call intent",
    "READ_CALENDAR": "calendar database read",
    "WRITE_CALENDAR": "calendar database write",
    "ACCESS_FINE_LOCATION": "precise location",
    "ACCESS_COARSE_LOCATION": "coarse location",
    "LocationManager": "automatic device location",
    "com.google.android.gms.auth.api.signin": "Google Sign-In",
    "GoogleDriveHelper": "Google Drive integration",
    "LockScreenAccessibilityService": "inherited accessibility service",
    "WP8Migration": "Windows Phone migration",
    "api.github.com/repos/jovanovski": "Jovanovski updater endpoint",
    "gorjan.rocks": "original developer endpoint",
}

violations = []
for token, label in forbidden.items():
    locations = []
    for path, text in corpus.items():
        if token not in text:
            continue
        lines = text.splitlines()
        for line_no, line_text in enumerate(lines, start=1):
            if token in line_text:
                locations.append((path.relative_to(root), line_no, line_text.strip(), lines))
                if len(locations) >= 4:
                    break
        if len(locations) >= 4:
            break
    if locations:
        violations.append((label, token, locations))

print("\nSummary:")
print(f"  Feature checks present: {len(checks) + len(aol_checks) - len(missing)}/{len(checks) + len(aol_checks)} plus selector constraints")
if missing:
    print("  Missing/unverified requirements: " + ", ".join(missing))
else:
    print("  Requested visual/feature markers and selector constraints found.")

if violations:
    print("  FORBIDDEN REFERENCES FOUND:")
    printed_contexts = set()
    for label, token, locations in violations:
        print(f"   - {label}: {token}")
        for path, line_no, line_text, lines in locations:
            print(f"       {path}:{line_no}: {line_text}")
            key = (str(path), line_no)
            if key not in printed_contexts:
                printed_contexts.add(key)
                start = max(1, line_no - 5)
                end = min(len(lines), line_no + 7)
                print(f"       --- context {path}:{start}-{end} ---")
                for n in range(start, end + 1):
                    print(f"       {n:05d}: {lines[n - 1]}")
    raise SystemExit(1)

if missing:
    raise SystemExit(1)

print("  Privacy/architecture forbidden-reference audit: PASS")
