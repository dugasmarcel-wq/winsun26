from pathlib import Path
import re

root = Path("upstream")
main = root / "app/src/main"
java_root = main / "java/rocks/gorjan/gokixp"
main_activity = java_root / "MainActivity.kt"
theme_manager = java_root / "theme/ThemeManager.kt"

# Remove the retired Windows Phone handoff implementation entirely.
for retired in (java_root / "WP8Migration.kt", java_root / "WP8MigrationProvider.kt"):
    if retired.exists():
        retired.unlink()

# Complete Windows 7 as a separate persisted AppTheme. The masterpiece pass
# already wires Windows 7 through resource selection, using Vista resources as
# a temporary compatibility fallback where dedicated Windows 7 assets are absent.
t = theme_manager.read_text()
if "object Windows7 : AppTheme()" not in t:
    vista_object = '''    object WindowsVista : AppTheme() {
        override val customIconsKey = "custom_icons_vista"
        override fun toString() = "Windows Vista"
    }
'''
    windows7_object = vista_object + '''
    object Windows7 : AppTheme() {
        override val customIconsKey = "custom_icons_windows7"
        override fun toString() = "Windows 7"
    }
'''
    if vista_object not in t:
        raise SystemExit("Could not locate WindowsVista AppTheme definition")
    t = t.replace(vista_object, windows7_object, 1)

if '"Windows 7" -> Windows7' not in t:
    t = t.replace(
        '            "Windows Vista" -> WindowsVista\n',
        '            "Windows Vista" -> WindowsVista\n            "Windows 7" -> Windows7\n',
        1,
    )

all_match = re.search(r'fun all\(\): List<AppTheme> = listOf\(([^)]*)\)', t)
if all_match and "Windows7" not in all_match.group(1):
    items = all_match.group(1).rstrip()
    replacement = f'fun all(): List<AppTheme> = listOf({items}, Windows7)'
    t = t[:all_match.start()] + replacement + t[all_match.end():]

theme_manager.write_text(t)

s = main_activity.read_text()

# Remove original-developer destinations.
for inherited_url in (
    "https://gorjan.rocks/clients/marti/",
    "https://gorjan.rocks",
    "https://github.com/jovanovski/windowslauncher/",
):
    s = s.replace(inherited_url, "about:blank")

# AirCare/location was intentionally removed. Keep any surviving UI reference
# local instead of restoring the inherited AQI backend.
s = s.replace("AIRCARE_URL", '"about:blank"')

# Remove the obsolete Windows Phone first-run branch by anchoring it between
# stable surrounding statements instead of depending on its internal formatting.
s = re.sub(
    r'\n\s*if \(wasWindowsPhoneUser\b.*?\n\s*if \(shownForVersion != currentVersion\)',
    '\n\n        if (shownForVersion != currentVersion)',
    s,
    flags=re.S,
)

# Remove the companion-launcher notice and keyboard probe methods.
s = re.sub(
    r'\n\s*private fun showWindowsPhoneMovedNotice\(\) \{.*?\n\s*private fun showWelcomeToWindows\(',
    '\n\n    private fun showWelcomeToWindows(',
    s,
    flags=re.S,
)

# Remove a leftover companion URL declaration if the upstream source still has one.
s = re.sub(r'^\s*(?:private\s+)?(?:const\s+)?val\s+WINDOWS_PHONE_LAUNCHER_URL\s*=.*\n', '', s, flags=re.M)

# Defensive cleanup for references left only in comments or dead source after the
# structural removals above.
s = s.replace("WP8Migration.KEY_NOTICE_SHOWN", '"winsung_retired_wp8_notice"')
s = s.replace("WP8Migration", "RetiredWindowsPhoneMigration")

# Replace inherited developer/update copy. A callable replacement preserves the
# backslash-n escapes required inside a normal Kotlin string literal.
welcome_pattern = r'^\s*val welcomeMessage = "Windows has updated to version \$versionName,.*?"$'
welcome_replacement = (
    '        val welcomeMessage = "Welcome to WINSUNG $versionName.\\n\\n'
    'This is a local-first Windows-style launcher build. Network access is used only for '
    'features you directly open, such as browsing and Quick Glance news.\\n\\n'
    'Use the desktop, Start menu, and appearance controls to switch between the available '
    'Windows environments."'
)
s = re.sub(welcome_pattern, lambda _m: welcome_replacement, s, flags=re.M)

# Disable inherited remote changelog retrieval while preserving the UI callback.
s = re.sub(
    r'\n\s*// Function to format changelog text\n\s*fun fetchChangeLogFromGitHub\(callback: \(String\) -> Unit\) \{.*?\n\s*\}\n\n\s*// Set welcome message with automatic link detection',
    '\n\n        fun fetchChangeLogFromGitHub(callback: (String) -> Unit) {\n            callback("Remote changelog checks are disabled in WINSUNG.")\n        }\n\n        // Set welcome message with automatic link detection',
    s,
    flags=re.S,
)

s = s.replace("https://api.github.com/repos/jovanovski/windowslauncher/releases", "about:blank")
s = s.replace("https://github.com/jovanovski/windowslauncher/releases", "about:blank")
main_activity.write_text(s)

blocked = (
    "api.github.com/repos/jovanovski",
    "open-meteo",
    "getaircare",
    "gorjan.rocks",
    "tetyys.com",
    "GoogleDriveHelper",
    "GoogleSignIn",
    "LockScreenAccessibilityService",
    "WP8Migration",
    "WINDOWS_PHONE_LAUNCHER_URL",
)

hits = []
for path in list((main / "java").rglob("*.kt")) + [main / "AndroidManifest.xml"]:
    text = path.read_text(errors="ignore")
    for token in blocked:
        if token in text:
            hits.append(f"{path}: {token}")

if hits:
    raise SystemExit("Blocked inherited runtime references remain:\n" + "\n".join(hits))

print("WINSUNG post-masterpiece privacy hardening complete")
