from pathlib import Path

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
controller_text = controller_path.read_text(errors="ignore") if controller_path.exists() else ""
controller_upper = controller_text.upper()

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
    "Windows Classic": ["Windows Classic"],
    "Windows XP": ["Windows XP"],
    "Windows Vista": ["Windows Vista"],
    "Windows 7": ["Windows 7"],
    "Win7 independent icon prefs": ["custom_icons_windows7"],
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
        print(f"PASS | {label:<30} | {hit}")
    else:
        print(f"MISS | {label}")
        missing.append(label)

for label, needle in aol_checks.items():
    if needle in controller_upper:
        line = controller_upper[:controller_upper.index(needle)].count("\n") + 1
        print(f"PASS | {label:<30} | winsung/Winsung98Controller.kt:{line} [{needle}]")
    else:
        print(f"MISS | {label}")
        missing.append(label)

forbidden = {
    "QUERY_ALL_PACKAGES": "broad installed-app visibility",
    "MANAGE_EXTERNAL_STORAGE": "broad storage access",
    "READ_CONTACTS": "contacts access",
    "CALL_PHONE": "direct calling permission",
    "READ_CALENDAR": "calendar database read",
    "WRITE_CALENDAR": "calendar database write",
    "ACCESS_FINE_LOCATION": "precise location",
    "ACCESS_COARSE_LOCATION": "coarse location",
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
print(f"  Feature checks present: {len(checks) + len(aol_checks) - len(missing)}/{len(checks) + len(aol_checks)}")
if missing:
    print("  Missing/unverified feature markers: " + ", ".join(missing))
else:
    print("  All requested feature markers found.")

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
                start = max(1, line_no - 7)
                end = min(len(lines), line_no + 9)
                print(f"       --- context {path}:{start}-{end} ---")
                for n in range(start, end + 1):
                    print(f"       {n:05d}: {lines[n - 1]}")
    raise SystemExit(1)

print("  Privacy/architecture forbidden-reference audit: PASS")
