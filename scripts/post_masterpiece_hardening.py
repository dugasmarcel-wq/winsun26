from pathlib import Path
import re

root = Path("upstream")
main = root / "app/src/main"
main_activity = main / "java/rocks/gorjan/gokixp/MainActivity.kt"

s = main_activity.read_text()

# Do not retain original-developer destinations. Keep behavior compile-safe and local.
for inherited_url in (
    "https://gorjan.rocks/clients/marti/",
    "https://gorjan.rocks",
    "https://github.com/jovanovski/windowslauncher/",
):
    s = s.replace(inherited_url, "about:blank")

# Replace the inherited welcome copy with WINSUNG-owned local copy.
s = re.sub(
    r'^\s*val welcomeMessage = "Windows has updated to version \$versionName,.*?"$',
    '        val welcomeMessage = "Welcome to WINSUNG $versionName.\\n\\nThis is a local-first Windows-style launcher build. Network access is used only for features you directly open, such as browsing and Quick Glance news.\\n\\nUse the desktop, Start menu, and appearance controls to switch between the available Windows environments."',
    s,
    flags=re.M,
)

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
