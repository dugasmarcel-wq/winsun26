from pathlib import Path
import re

root = Path("upstream")
main = root / "app/src/main"
java_root = main / "java/rocks/gorjan/gokixp"
main_activity = java_root / "MainActivity.kt"
theme_manager = java_root / "theme/ThemeManager.kt"
dialer = java_root / "apps/dialer/DialerApp.kt"
quick_widget = java_root / "quickglance/QuickGlanceWidget.kt"
calendar_provider = java_root / "quickglance/CalendarDataProvider.kt"


def _matching_brace(text: str, opening: int) -> int:
    """Find a Kotlin block's closing brace while ignoring comments and strings."""
    depth = 0
    i = opening
    state = "code"
    while i < len(text):
        if state == "code":
            if text.startswith('//', i):
                state = "line_comment"; i += 2; continue
            if text.startswith('/*', i):
                state = "block_comment"; i += 2; continue
            if text.startswith('"""', i):
                state = "triple"; i += 3; continue
            ch = text[i]
            if ch == '"': state = "string"; i += 1; continue
            if ch == "'": state = "char"; i += 1; continue
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: return i
            i += 1
        elif state == "line_comment":
            if text[i] == '\n': state = "code"
            i += 1
        elif state == "block_comment":
            if text.startswith('*/', i): state = "code"; i += 2
            else: i += 1
        elif state == "triple":
            if text.startswith('"""', i): state = "code"; i += 3
            else: i += 1
        elif state == "string":
            if text[i] == '\\': i += 2
            elif text[i] == '"': state = "code"; i += 1
            else: i += 1
        elif state == "char":
            if text[i] == '\\': i += 2
            elif text[i] == "'": state = "code"; i += 1
            else: i += 1
    raise ValueError("Unbalanced Kotlin block")


def replace_function_body(text: str, name: str, body: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf'(?m)^(?P<indent>[ \t]*)(?:(?:private|public|protected|internal|override|suspend)\s+)*fun\s+{re.escape(name)}\s*\('
    )
    m = pattern.search(text)
    if not m:
        return text, False
    brace = text.find('{', m.end())
    if brace < 0:
        return text, False
    # Do not accidentally consume a later function if this one is expression-bodied.
    between = text[m.end():brace]
    if '=' in between and '\n' in between:
        return text, False
    end = _matching_brace(text, brace)
    indent = m.group('indent')
    lines = body.strip('\n').splitlines()
    formatted = '\n' + '\n'.join(indent + '    ' + line if line else '' for line in lines) + '\n' + indent
    return text[:brace + 1] + formatted + text[end:]


# Remove the retired Windows Phone handoff implementation entirely.
for retired in (java_root / "WP8Migration.kt", java_root / "WP8MigrationProvider.kt"):
    if retired.exists():
        retired.unlink()

# Complete Windows 7 as a separate persisted AppTheme. The masterpiece pass
# already wires Windows 7 through resource selection, using Vista resources as
# a temporary compatibility fallback where dedicated Windows 7 assets are absent.
t = theme_manager.read_text()
if not re.search(r'^\s*object Windows7\s*:\s*AppTheme\(\)', t, flags=re.M):
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

s = re.sub(r'^\s*(?:private\s+)?(?:const\s+)?val\s+WINDOWS_PHONE_LAUNCHER_URL\s*=.*\n', '', s, flags=re.M)
s = s.replace("WP8Migration.KEY_NOTICE_SHOWN", '"winsung_retired_wp8_notice"')
s = s.replace("WP8Migration", "RetiredWindowsPhoneMigration")

# Remove the inherited direct-call/contact permission prompt from the internal dialer window.
s = re.sub(
    r'(\n\s*private fun createAndShowDialerDialog\(\) \{)\s*\n\s*// Request permissions when opening dialer\s*\n\s*if \(checkSelfPermission\(android\.Manifest\.permission\.CALL_PHONE\).*?\n\s*\}\s*\n',
    r'\1\n',
    s,
    count=1,
    flags=re.S,
)

# The legacy floating Quick Glance widget no longer reads the calendar database.
s, _ = replace_function_body(s, "requestCalendarPermission", "return")

# Broad-storage code is retired; file selection is through Android document pickers.
s, _ = replace_function_body(s, "hasStoragePermission", "return false")
s, _ = replace_function_body(s, "requestStoragePermission", "return")

# Disable inherited automatic weather/location/AQI behavior. WINSUNG weather is
# explicitly user initiated from AOL and can open a selected app/site without location.
weather_bodies = {
    "setupWeatherUpdates": '''
findViewById<View>(R.id.aqi_container)?.visibility = View.GONE
findViewById<View>(R.id.weather_temp)?.visibility = View.GONE
weatherUpdateRunnable = null''',
    "initializeAqiDisplay": '''
findViewById<View>(R.id.aqi_container)?.visibility = View.GONE''',
    "handleAqiTap": "return",
    "openPlayStoreForAqiApp": "return",
    "refreshAqiData": "return",
    "scheduleWeatherUpdates": "weatherUpdateRunnable = null",
    "handleWeatherTempTap": "launchDefaultWeatherApp()",
    "launchDefaultWeatherApp": '''
try {
    startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://www.weather.com/")))
} catch (_: Exception) {
    winsungShowToast("No weather app or browser is available")
}''',
    "launchGoogleWeatherApp": "launchDefaultWeatherApp()",
    "handleWeatherTempRefresh": "return",
    "updateWeatherTemperature": '''
findViewById<View>(R.id.weather_temp)?.visibility = View.GONE''',
    "fetchLocationAndWeather": "return",
    "fetchWeatherData": "return",
    "fetchAqiData": "return",
    "updateAqiDisplay": '''
findViewById<View>(R.id.aqi_container)?.visibility = View.GONE''',
    "refreshWeatherIfNeeded": "return",
}
for name, body in weather_bodies.items():
    s, _ = replace_function_body(s, name, body)

# Drop location/calendar permission-result branches while retaining notification/media branches.
s = re.sub(
    r'\n\s*LOCATION_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*CALENDAR_PERMISSION_REQUEST_CODE\s*->',
    '\n            CALENDAR_PERMISSION_REQUEST_CODE ->',
    s,
    count=1,
    flags=re.S,
)
s = re.sub(
    r'\n\s*CALENDAR_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*AUDIO_PERMISSION_REQUEST_CODE\s*->',
    '\n            AUDIO_PERMISSION_REQUEST_CODE ->',
    s,
    count=1,
    flags=re.S,
)

# Package visibility is intentionally scoped; remove the obsolete broad-visibility claim.
s = s.replace(
    '// QUERY_ALL_PACKAGES is held, so "not found" here means genuinely not installed\n        // rather than merely not visible to this app.',
    '// Package lookups are limited to launcher-visible/explicitly queried apps.'
)

# Replace inherited developer/update copy.
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

# Internal dialer: never query contacts and never place a call directly. Android's
# dialer remains the confirmation boundary via ACTION_DIAL.
if dialer.exists():
    d = dialer.read_text()
    d, _ = replace_function_body(d, "callContact", '''
onSoundPlay(R.raw.click)
try {
    val intent = Intent(Intent.ACTION_DIAL)
    intent.data = Uri.parse("tel:$phoneNumber")
    context.startActivity(intent)
} catch (e: Exception) {
    Log.e("DialerApp", "Error opening system dialer", e)
}''')
    d, _ = replace_function_body(d, "searchContacts", "return emptyList()")
    dialer.write_text(d)

# Retired floating Quick Glance calendar integration must not trigger permission access.
if quick_widget.exists():
    q = quick_widget.read_text()
    q, _ = replace_function_body(q, "hasCalendarPermission", "return false")
    q, _ = replace_function_body(q, "handleCalendarPermissionGranted", "return")
    quick_widget.write_text(q)

# Keep the class shape expected by the old widget, but remove every calendar DB query.
if calendar_provider.exists():
    calendar_provider.write_text('''package rocks.gorjan.gokixp.quickglance

import android.content.Context

/**
 * Compatibility provider retained for the legacy floating Quick Glance widget.
 * WINSUNG does not read the device calendar database; calendar actions launch the
 * user's calendar application explicitly instead.
 */
class CalendarDataProvider(private val context: Context) : QuickGlanceDataProvider {
    private var callback: ((QuickGlanceData?) -> Unit)? = null

    override suspend fun getCurrentData(): QuickGlanceData? = null

    override fun startUpdates(callback: (QuickGlanceData?) -> Unit) {
        this.callback = callback
        callback(null)
    }

    override fun stopUpdates() {
        callback = null
    }

    override fun getProviderId(): String = "calendar_disabled"

    fun forceRefresh() {
        callback?.invoke(null)
    }
}
''')

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
