from pathlib import Path
import re

root = Path("upstream")
main = root / "app/src/main"
java = main / "java/rocks/gorjan/gokixp"
main_activity = java / "MainActivity.kt"
theme_manager = java / "theme/ThemeManager.kt"
dialer = java / "apps/dialer/DialerApp.kt"
quick_widget = java / "quickglance/QuickGlanceWidget.kt"
calendar_provider = java / "quickglance/CalendarDataProvider.kt"


def matching_brace(text: str, opening: int) -> int:
    depth = 0
    i = opening
    state = "code"
    while i < len(text):
        if state == "code":
            if text.startswith("//", i): state = "line"; i += 2; continue
            if text.startswith("/*", i): state = "block"; i += 2; continue
            if text.startswith('"""', i): state = "triple"; i += 3; continue
            ch = text[i]
            if ch == '"': state = "string"; i += 1; continue
            if ch == "'": state = "char"; i += 1; continue
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return i
            i += 1
        elif state == "line":
            if text[i] == "\n": state = "code"
            i += 1
        elif state == "block":
            if text.startswith("*/", i): state = "code"; i += 2
            else: i += 1
        elif state == "triple":
            if text.startswith('"""', i): state = "code"; i += 3
            else: i += 1
        elif state == "string":
            if text[i] == "\\": i += 2
            elif text[i] == '"': state = "code"; i += 1
            else: i += 1
        elif state == "char":
            if text[i] == "\\": i += 2
            elif text[i] == "'": state = "code"; i += 1
            else: i += 1
    raise RuntimeError("unbalanced Kotlin block")


def replace_body(text: str, name: str, body: str) -> str:
    pat = re.compile(rf'(?m)^(?P<i>[ \t]*)(?:(?:private|public|protected|internal|override|suspend)\s+)*fun\s+{re.escape(name)}\s*\(')
    m = pat.search(text)
    if not m:
        return text
    brace = text.find("{", m.end())
    if brace < 0:
        return text
    end = matching_brace(text, brace)
    indent = m.group("i")
    body_lines = body.strip("\n").splitlines()
    replacement = "\n" + "\n".join(indent + "    " + x if x else "" for x in body_lines) + "\n" + indent
    return text[:brace + 1] + replacement + text[end:]


# Remove retired Windows Phone migration sources.
for p in (java / "WP8Migration.kt", java / "WP8MigrationProvider.kt"):
    if p.exists(): p.unlink()

# Ensure Windows 7 has its own persisted theme identity.
t = theme_manager.read_text()
if not re.search(r'^\s*object Windows7\s*:\s*AppTheme\(\)', t, re.M):
    anchor = '''    object WindowsVista : AppTheme() {
        override val customIconsKey = "custom_icons_vista"
        override fun toString() = "Windows Vista"
    }
'''
    if anchor not in t:
        raise SystemExit("WindowsVista AppTheme anchor not found")
    t = t.replace(anchor, anchor + '''
    object Windows7 : AppTheme() {
        override val customIconsKey = "custom_icons_windows7"
        override fun toString() = "Windows 7"
    }
''', 1)
if '"Windows 7" -> Windows7' not in t:
    t = t.replace('            "Windows Vista" -> WindowsVista\n', '            "Windows Vista" -> WindowsVista\n            "Windows 7" -> Windows7\n', 1)
all_m = re.search(r'fun all\(\): List<AppTheme> = listOf\(([^)]*)\)', t)
if all_m and "Windows7" not in all_m.group(1):
    t = t[:all_m.start()] + f'fun all(): List<AppTheme> = listOf({all_m.group(1).rstrip()}, Windows7)' + t[all_m.end():]
theme_manager.write_text(t)

s = main_activity.read_text()

# Original developer/update destinations are not WINSUNG runtime services.
for old in (
    "https://gorjan.rocks/clients/marti/",
    "https://gorjan.rocks",
    "https://github.com/jovanovski/windowslauncher/",
    "https://api.github.com/repos/jovanovski/windowslauncher/releases",
    "https://github.com/jovanovski/windowslauncher/releases",
):
    s = s.replace(old, "about:blank")
s = s.replace("AIRCARE_URL", '"about:blank"')

# Remove obsolete Windows Phone branches/notice methods.
s = re.sub(r'\n\s*if \(wasWindowsPhoneUser\b.*?\n\s*if \(shownForVersion != currentVersion\)', '\n\n        if (shownForVersion != currentVersion)', s, flags=re.S)
s = re.sub(r'\n\s*private fun showWindowsPhoneMovedNotice\(\) \{.*?\n\s*private fun showWelcomeToWindows\(', '\n\n    private fun showWelcomeToWindows(', s, flags=re.S)
s = re.sub(r'^\s*(?:private\s+)?(?:const\s+)?val\s+WINDOWS_PHONE_LAUNCHER_URL\s*=.*\n', '', s, flags=re.M)
s = s.replace("WP8Migration.KEY_NOTICE_SHOWN", '"winsung_retired_wp8_notice"').replace("WP8Migration", "RetiredWindowsPhoneMigration")

# Remove the inherited direct-call/contact permission prompt from the internal dialer UI.
s = re.sub(
    r'(\n\s*private fun createAndShowDialerDialog\(\) \{)\s*\n\s*// Request permissions when opening dialer\s*\n\s*if \(checkSelfPermission\(android\.Manifest\.permission\.CALL_PHONE\).*?\n\s*\}\s*\n',
    r'\1\n', s, count=1, flags=re.S,
)

# No calendar DB permission, no broad storage permission path.
s = replace_body(s, "requestCalendarPermission", "return")
s = replace_body(s, "hasStoragePermission", "return false")
s = replace_body(s, "requestStoragePermission", "return")

# No inherited automatic location/weather/AQI system. AOL Weather is user initiated.
weather = {
    "setupWeatherUpdates": 'findViewById<View>(R.id.aqi_container)?.visibility = View.GONE\nfindViewById<View>(R.id.weather_temp)?.visibility = View.GONE\nweatherUpdateRunnable = null',
    "initializeAqiDisplay": 'findViewById<View>(R.id.aqi_container)?.visibility = View.GONE',
    "handleAqiTap": "return",
    "openPlayStoreForAqiApp": "return",
    "refreshAqiData": "return",
    "scheduleWeatherUpdates": "weatherUpdateRunnable = null",
    "handleWeatherTempTap": "launchDefaultWeatherApp()",
    "launchDefaultWeatherApp": 'try {\n    startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse("https://www.weather.com/")))\n} catch (_: Exception) {\n    winsungShowToast("No weather app or browser is available")\n}',
    "launchGoogleWeatherApp": "launchDefaultWeatherApp()",
    "handleWeatherTempRefresh": "return",
    "updateWeatherTemperature": 'findViewById<View>(R.id.weather_temp)?.visibility = View.GONE',
    "fetchLocationAndWeather": "return",
    "fetchWeatherData": "return",
    "fetchAqiData": "return",
    "updateAqiDisplay": 'findViewById<View>(R.id.aqi_container)?.visibility = View.GONE',
    "refreshWeatherIfNeeded": "return",
}
for name, body in weather.items():
    s = replace_body(s, name, body)

# Delete obsolete location/calendar request-result branches while keeping media/notification handling.
s = re.sub(r'\n\s*LOCATION_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*CALENDAR_PERMISSION_REQUEST_CODE\s*->', '\n            CALENDAR_PERMISSION_REQUEST_CODE ->', s, count=1, flags=re.S)
s = re.sub(r'\n\s*CALENDAR_PERMISSION_REQUEST_CODE\s*->\s*if\b.*?\n\s*AUDIO_PERMISSION_REQUEST_CODE\s*->', '\n            AUDIO_PERMISSION_REQUEST_CODE ->', s, count=1, flags=re.S)

# Remove stale claim about QUERY_ALL_PACKAGES; WINSUNG uses scoped package visibility.
s = s.replace('// QUERY_ALL_PACKAGES is held, so "not found" here means genuinely not installed\n        // rather than merely not visible to this app.', '// Package lookups are limited to launcher-visible/explicitly queried apps.')

# Registry Editor cleanup is a no-op upstream and may be reintroduced by the masterpiece pass.
s = re.sub(r'(?m)^\s*regeditApp\.cleanup\(\)\s*$', '', s)

# Local-first welcome text and no remote changelog polling.
s = re.sub(
    r'^\s*val welcomeMessage = "Windows has updated to version \$versionName,.*?"$',
    lambda _: '        val welcomeMessage = "Welcome to WINSUNG $versionName.\\n\\nThis is a local-first Windows-style launcher build. Network access is used only for features you directly open, such as browsing and Quick Glance news.\\n\\nUse the desktop, Start menu, and appearance controls to switch between the available Windows environments."',
    s, flags=re.M,
)
s = re.sub(
    r'\n\s*// Function to format changelog text\n\s*fun fetchChangeLogFromGitHub\(callback: \(String\) -> Unit\) \{.*?\n\s*\}\n\n\s*// Set welcome message with automatic link detection',
    '\n\n        fun fetchChangeLogFromGitHub(callback: (String) -> Unit) {\n            callback("Remote changelog checks are disabled in WINSUNG.")\n        }\n\n        // Set welcome message with automatic link detection',
    s, flags=re.S,
)
main_activity.write_text(s)

# Internal dialer only hands the number to Android's dialer; it never reads contacts.
if dialer.exists():
    d = dialer.read_text()
    call_token = "fun callContact"
    call_pos = d.find(call_token)
    if call_pos < 0:
        raise SystemExit("Dialer callContact function not found")
    call_start = d.rfind("\n", 0, call_pos) + 1
    call_brace = d.find("{", call_pos)
    if call_brace < 0:
        raise SystemExit("Dialer callContact body not found")
    call_end = matching_brace(d, call_brace)
    call_prefix = d[call_start:call_pos]
    call_indent = call_prefix[: len(call_prefix) - len(call_prefix.lstrip())]
    call_replacement = (
        call_indent + "private fun callContact(phoneNumber: String) {\n"
        + call_indent + "    onSoundPlay(R.raw.click)\n"
        + call_indent + "    try {\n"
        + call_indent + "        val intent = Intent(Intent.ACTION_DIAL)\n"
        + call_indent + '        intent.data = Uri.parse("tel:$phoneNumber")\n'
        + call_indent + "        context.startActivity(intent)\n"
        + call_indent + "    } catch (e: Exception) {\n"
        + call_indent + '        Log.e("DialerApp", "Error opening system dialer", e)\n'
        + call_indent + "    }\n"
        + call_indent + "}"
    )
    d = d[:call_start] + call_replacement + d[call_end + 1:]
    # Replace the complete declaration by function name. Avoid depending on the
    # generator's exact signature formatting.
    search_token = "fun searchContacts"
    search_pos = d.find(search_token)
    if search_pos < 0:
        raise SystemExit("Dialer searchContacts function not found")
    search_start = d.rfind("\n", 0, search_pos) + 1
    search_brace = d.find("{", search_pos)
    if search_brace < 0:
        raise SystemExit("Dialer searchContacts body not found")
    search_end = matching_brace(d, search_brace)
    line_prefix = d[search_start:search_pos]
    indent = line_prefix[: len(line_prefix) - len(line_prefix.lstrip())]
    replacement = (
        indent + "private fun searchContacts(query: String): List<ContactInfo> {\n"
        + indent + '    @Suppress("UNUSED_VARIABLE")\n'
        + indent + "    val ignoredQuery = query\n"
        + indent + "    return emptyList<ContactInfo>()\n"
        + indent + "}"
    )
    d = d[:search_start] + replacement + d[search_end + 1:]
    dialer.write_text(d)

# Legacy floating Quick Glance widget is retained only as a compatibility surface;
# it no longer requests or consumes calendar data.
if quick_widget.exists():
    q = quick_widget.read_text()
    q = replace_body(q, "hasCalendarPermission", "return false")
    q = replace_body(q, "handleCalendarPermissionGranted", "return")
    quick_widget.write_text(q)

if calendar_provider.exists():
    calendar_provider.write_text('''package rocks.gorjan.gokixp.quickglance

import android.content.Context

class CalendarDataProvider(private val context: Context) : QuickGlanceDataProvider {
    private var callback: ((QuickGlanceData?) -> Unit)? = null
    override suspend fun getCurrentData(): QuickGlanceData? = null
    override fun startUpdates(callback: (QuickGlanceData?) -> Unit) { this.callback = callback; callback(null) }
    override fun stopUpdates() { callback = null }
    override fun getProviderId(): String = "calendar_disabled"
    fun forceRefresh() { callback?.invoke(null) }
}
''')

# The generator must never reintroduce these runtime systems unnoticed.
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
    txt = path.read_text(errors="ignore")
    for token in blocked:
        if token in txt:
            hits.append(f"{path}: {token}")
if hits:
    raise SystemExit("Blocked inherited runtime references remain:\n" + "\n".join(hits))

print("WINSUNG deterministic generated-source hardening complete")
