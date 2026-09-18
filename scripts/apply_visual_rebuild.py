from pathlib import Path
import re
import shutil

root = Path("upstream")
main = root / "app/src/main"
java_root = main / "java/rocks/gorjan/gokixp"
overlay = Path("overlay/app/src/main/java/rocks/gorjan/gokixp/winsung/Winsung98Controller.kt")
controller = java_root / "winsung/Winsung98Controller.kt"
theme_manager = java_root / "theme/ThemeManager.kt"
main_activity = java_root / "MainActivity.kt"

if not overlay.exists():
    raise SystemExit(f"Visual overlay is missing: {overlay}")
controller.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(overlay, controller)

# Use the native/Jovanovski asset library for application shortcuts.  The old
# WINSUNG APK is a visual/layout reference only; its WebView/icon runtime is not
# transplanted into the native launcher.
s = controller.read_text()
asset_map = {
    'winsung_fixed/phone.png': 'custom_icons_98/Phone.webp',
    'winsung_fixed/signal.png': 'custom_icons_98/accessibility_window_signal.webp',
    'winsung_fixed/firefox.png': 'custom_icons/Internet Explorer 6.webp',
    'winsung_fixed/whatsapp.png': 'custom_icons_98/WhatsApp.webp',
    'winsung_fixed/ytmusic.png': 'custom_icons_programs/YouTube.webp',
}
for old, new in asset_map.items():
    s = s.replace(old, new)
controller.write_text(s)

# The native implementation internally keeps the historical WindowsClassic
# object name because a large amount of Jovanovski code keys off that sealed
# object.  User-facing identity is Windows 98 only.
t = theme_manager.read_text()
t = re.sub(
    r'(object\s+WindowsClassic\s*:\s*AppTheme\(\)\s*\{.*?override\s+fun\s+toString\(\)\s*=\s*)"Windows Classic"',
    r'\1"Windows 98"',
    t,
    flags=re.S,
)

# Accept the legacy stored value on upgrade, but only write/display Windows 98.
t = re.sub(
    r'"Windows Classic"\s*->\s*WindowsClassic',
    '"Windows Classic", "Windows 98" -> WindowsClassic',
    t,
    count=1,
)
if '"Windows 98" -> WindowsClassic' not in t and '"Windows Classic", "Windows 98" -> WindowsClassic' not in t:
    t = t.replace('fun fromString(value: String?): AppTheme = when (value) {',
                  'fun fromString(value: String?): AppTheme = when (value) {\n            "Windows 98" -> WindowsClassic', 1)

# Exactly three user-selectable environments in the requested order.
t = re.sub(
    r'fun\s+all\(\)\s*:\s*List<AppTheme>\s*=\s*listOf\([^)]*\)',
    'fun all(): List<AppTheme> = listOf(WindowsClassic, WindowsXP, WindowsVista)',
    t,
    count=1,
)

# Win98 is the factory/default shell.
t = t.replace('prefs.getString(KEY_SELECTED_THEME, "Windows XP")',
              'prefs.getString(KEY_SELECTED_THEME, "Windows 98")')
t = re.sub(r'else\s*->\s*WindowsXP\s*//\s*Default to XP if unknown',
           'else -> WindowsClassic // WINSUNG factory default: Windows 98', t)

# Do not expose Plus!/95/2000-style sub-theme clutter in WINSUNG.  Supporting
# helper code can remain for compatibility but there are no selectable entries
# and no active legacy sub-theme.
t = re.sub(r'fun getAllPlus95Themes\(\): List<Plus95Theme> = PLUS95_THEMES',
           'fun getAllPlus95Themes(): List<Plus95Theme> = emptyList()', t)
t = re.sub(
    r'fun getActivePlus95\(\): Plus95Theme\?\s*\{.*?\n\s*\}',
    'fun getActivePlus95(): Plus95Theme? = null',
    t,
    count=1,
    flags=re.S,
)
theme_manager.write_text(t)

# Remove the legacy name from user-facing copy while retaining AppTheme.WindowsClassic
# identifiers in source.  This catches appearance/spinner labels created in MainActivity.
m = main_activity.read_text()
m = m.replace('"Windows Classic"', '"Windows 98"')

# A launcher must actually enumerate launchable applications. On a fresh install
# seed the native XP/Vista pinned area with useful built-in programs; once the
# user changes pins, their saved list is left alone.
pinned_anchor = '''    private fun getPinnedApps(): List<String> {
        val prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
'''
pinned_insert = '''    private fun getPinnedApps(): List<String> {
        val prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE)

        if (!prefs.contains(KEY_PINNED_APPS)) {
            val defaults = listOf(
                "system.internet_explorer",
                "system.notepad",
                "system.wmp",
                "system.clock",
                "system.minesweeper",
                "system.solitare",
                "system.pinball"
            )
            prefs.edit().putString(KEY_PINNED_APPS, defaults.joinToString(",")).apply()
        }
'''
if pinned_anchor not in m:
    raise SystemExit('getPinnedApps anchor not found')
m = m.replace(pinned_anchor, pinned_insert, 1)

# Clippy/agents are not part of the custom Windows 98 default desktop. Preserve
# Jovanovski's normal agent behavior for XP and Vista.
m = m.replace(
    '        agentView.visibility = if (isRoverVisible()) View.VISIBLE else View.GONE',
    '        agentView.visibility = if (themeManager.getSelectedTheme() is AppTheme.WindowsClassic) View.GONE else if (isRoverVisible()) View.VISIBLE else View.GONE',
    1,
)

# The inherited updater is removed, so don't leave a dead Windows Update row in
# XP/Vista Start menus.
m = m.replace(
    '            val updateItem = findViewById<LinearLayout>(R.id.windows_update_item)',
    '            val updateItem = findViewById<LinearLayout>(R.id.windows_update_item)\n            updateItem?.visibility = View.GONE',
    1,
)

# WINSUNG exposes only Windows 98 / XP / Vista.  The upstream Classic flavour
# picker (95/98/ME/2000) is intentionally hidden instead of presenting it as a
# second competing "Windows version" selector.
flavour_block = '''    private fun shouldShowFlavourSpinner(theme: AppTheme? = null): Boolean {
        var checkTheme = theme
        if(checkTheme == null){
            checkTheme = themeManager.getSelectedTheme()
        }
        return checkTheme is AppTheme.WindowsClassic
    }'''
if flavour_block in m:
    m = m.replace(
        flavour_block,
        '    private fun shouldShowFlavourSpinner(theme: AppTheme? = null): Boolean = false',
        1,
    )
main_activity.write_text(m)

# Final manifest scrub after every generator/hardening pass. The notification
# listener uses the service-level bind permission rather than a uses-permission
# grant. QUERY_ALL_PACKAGES is required by a launcher, REQUEST_DELETE_PACKAGES
# backs the user-confirmed uninstall action, and MANAGE_EXTERNAL_STORAGE backs
# the explicitly-opened Windows Explorer.
manifest = main / "AndroidManifest.xml"
ms = manifest.read_text()
for perm in (
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE",
):
    ms = re.sub(
        r'\s*<uses-permission\s+android:name="' + re.escape(perm) + r'"[^>]*/>',
        '',
        ms,
        flags=re.S,
    )
for required_perm in (
    "android.permission.QUERY_ALL_PACKAGES",
    "android.permission.REQUEST_DELETE_PACKAGES",
    "android.permission.MANAGE_EXTERNAL_STORAGE",
):
    if required_perm not in ms:
        raise SystemExit(f"Required launcher capability missing from manifest: {required_perm}")
manifest.write_text(ms)

# Sanity-check the visual shell before compiling.
controller_text = controller.read_text()
required = (
    'class ClassicBevelDrawable',
    'class QuickGlancePage',
    'class SecondaryPage',
    'class AolBackdrop',
    'class AolChannelView',
    'R.id.taskbar_empty_space',
    'badgeTick',
    'custom_icons_98/Phone.webp',
    'custom_icons_98/WhatsApp.webp',
    'custom_icons_programs/YouTube.webp',
)
missing = [x for x in required if x not in controller_text]
if missing:
    raise SystemExit('Visual rebuild is incomplete; missing: ' + ', '.join(missing))

if 'fun all(): List<AppTheme> = listOf(WindowsClassic, WindowsXP, WindowsVista)' not in t:
    raise SystemExit('Theme selector was not reduced to exactly Win98/XP/Vista')
if 'override fun toString() = "Windows 98"' not in t:
    raise SystemExit('Windows 98 display identity was not applied')

print('WINSUNG visual-first Win98 reconstruction applied')
