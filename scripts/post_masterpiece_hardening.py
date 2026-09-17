from pathlib import Path
import re

root = Path("upstream")
main = root / "app/src/main"
main_activity = main / "java/rocks/gorjan/gokixp/MainActivity.kt"
theme_manager = main / "java/rocks/gorjan/gokixp/theme/ThemeManager.kt"

# ---------------------------------------------------------------------------
# Theme completion
# ---------------------------------------------------------------------------
# The masterpiece pass wires Windows 7 through the launcher's resource maps,
# but v2.1.0 has no Windows7 AppTheme object. Define it as its own persisted
# theme. The generated resource mappings intentionally use Vista resources as
# the temporary compatibility fallback where dedicated Windows 7 assets are
# not present yet.
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
    t = t.replace('            "Windows Vista" -> WindowsVista\n',
                  '            "Windows Vista" -> WindowsVista\n            "Windows 7" -> Windows7\n', 1)

all_match = re.search(r'fun all\(\): List<AppTheme> = listOf\(([^)]*)\)', t)
if all_match and "Windows7" not in all_match.group(1):
    items = all_match.group(1).rstrip()
    replacement = f'fun all(): List<AppTheme> = listOf({items}, Windows7)'
    t = t[:all_match.start()] + replacement + t[all_match.end():]

theme_manager.write_text(t)

# ---------------------------------------------------------------------------
# MainActivity privacy and retired-feature cleanup
# ---------------------------------------------------------------------------
s = main_activity.read_text()

# Do not retain original-developer destinations. Keep behavior compile-safe and local.
for inherited_url in (
    "https://gorjan.rocks/clients/marti/",
    "https://gorjan.rocks",
    "https://github.com/jovanovski/windowslauncher/",
):
    s = s.replace(inherited_url, "about:blank")

# The inherited AQI/location backend was deliberately removed. Any UI remnant
# that still references the old constant gets a non-network destination rather
# than restoring AirCare or location access.
s = s.replace("AIRCARE_URL", '"about:blank"')

# Remove the old Windows Phone migration notice path. WINSUNG does not migrate
# data to another launcher and does not hand users to a companion-app URL.
s = re.sub(
    r'\n\s*if \(wasWindowsPhoneUser && !prefs\.getBoolean\(WP8Migration\.KEY_NOTICE_SHOWN, false\)\) \{.*?\n\s*return\n\s*\}\n',
    '\n',
    s,
    flags=re.S,
)
s = re.sub(
    r'\n\s*private fun showWindowsPhoneMovedNotice\(\) \{.*?\n\s*private fun showWelcomeToWindows\(',
    '\n\n    private fun showWelcomeToWindows(',
    s,
    flags=re.S,
)

# Replace inherited developer/update copy with WINSUNG-owned local copy. Use a
# callable replacement so the Kotlin source receives escaped \\n sequences rather
# than literal line breaks inside a quoted string.
welcome_pattern = r'^\s*val welcomeMessage = "Windows has updated to version \$versionName,.*?"$'
welcome_replacement = (
    '        val welcomeMessage = "Welcome to WINSUNG $versionName.\\n\\n'
    'This is a local-first Windows-style launcher build. Network access is used only for '
    'features you directly open, such as browsing and Quick Glance news.\\n\\n'
    'Use the desktop, Start menu, and appearance controls to switch between the available '
    'Windows environments."'
)
s = re.sub(welcome_pattern, lambda _m: welcome_replacement, s, flags=re.M)

# Disable inherited remote changelog retrieval while preserving the existing UI callback contract.
s = re.sub(
    r'\n\s*// Function to format changelog text\n\s*fun fetchChangeLogFromGitHub\(callback: \(String\) -> Unit\) \{.*?\n\s*\}\n\n\s*// Set welcome message with automatic link detection',
    '\n\n        fun fetchChangeLogFromGitHub(callback: (String) -> Unit) {\n            callback("Remote changelog checks are disabled in WINSUNG.")\n        }\n\n        // Set welcome message with automatic link detection',
    s,
    flags=re.S,
)

# Defense in depth: inherited update/release endpoints must never survive source generation.
s = s.replace("https://api.github.com/repos/jovanovski/windowslauncher/releases", "about:blank")
s = s.replace("https://github.com/jovanovski/windowslauncher/releases", "about:blank")

main_activity.write_text(s)

# Fail locally if a blocked inherited destination/component survived the transformations.
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
