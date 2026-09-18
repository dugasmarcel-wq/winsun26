from pathlib import Path
import re

root = Path('upstream')
app = root / 'app'
main = app / 'src/main'

# Build identity. Keep the original source namespace so the engine/resources stay intact.
gradle = app / 'build.gradle.kts'
s = gradle.read_text()
s = s.replace('applicationId = "rocks.gorjan.gokixp"', 'applicationId = "com.winsung.launcher"')
s = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 2', s)
s = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "1.1-winsung"', s)
# Remove Google Drive/account client dependencies only. Keep Gson because the launcher itself uses it locally.
s = re.sub(r'\n\s*// Google Drive API\n.*?\n\s*testImplementation', '\n\n    testImplementation', s, flags=re.S)
gradle.write_text(s)

# Privacy-focused manifest: keep launcher/network/notification essentials, remove personal-data permissions.
manifest = main / 'AndroidManifest.xml'
s = manifest.read_text()
for perm in [
    'android.permission.ACCESS_FINE_LOCATION', 'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.READ_CALENDAR', 'android.permission.WRITE_CALENDAR',
    'android.permission.READ_SYNC_SETTINGS', 'android.permission.WRITE_SYNC_SETTINGS',
    'android.permission.CALL_PHONE', 'android.permission.READ_CONTACTS',
    'android.permission.READ_EXTERNAL_STORAGE', 'android.permission.WRITE_EXTERNAL_STORAGE',
    'android.permission.READ_MEDIA_AUDIO', 'android.permission.READ_MEDIA_VIDEO', 'android.permission.READ_MEDIA_IMAGES'
]:
    s = re.sub(r'\s*<uses-permission\s+android:name="' + re.escape(perm) + r'"[^>]*/>', '', s, flags=re.S)
s = re.sub(r'\s*<permission\s+android:name="rocks\.gorjan\.gokixp\.permission\.READ_WP8_MIGRATION".*?/>', '', s, flags=re.S)

# Android 11+ package visibility: see launchable apps without QUERY_ALL_PACKAGES.
# The explicit packages cover the five fixed Win98 taskbar targets even if a
# vendor launcher intent is unusual.
if '<queries>' not in s:
    queries = '''\n    <queries>
        <intent>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent>
        <package android:name="com.samsung.android.dialer" />
        <package android:name="com.google.android.dialer" />
        <package android:name="org.thoughtcrime.securesms" />
        <package android:name="org.mozilla.firefox" />
        <package android:name="com.whatsapp" />
        <package android:name="com.google.android.apps.youtube.music" />
    </queries>\n'''
    s = re.sub(r'(<manifest\\b[^>]*>)', lambda m: m.group(1) + queries, s, count=1)
s = re.sub(r'\s*<!-- Accessibility Service for screen locking -->\s*<service\s+android:name="\.LockScreenAccessibilityService".*?</service>', '', s, flags=re.S)
s = re.sub(r'\s*<!--\s*Hands the Windows Phone.*?<provider\s+android:name="\.WP8MigrationProvider".*?/>', '', s, flags=re.S)
s = s.replace('android:allowBackup="true"', 'android:allowBackup="false"')
s = re.sub(r'\s*android:dataExtractionRules="@xml/data_extraction_rules"', '', s)
s = re.sub(r'\s*android:fullBackupContent="@xml/backup_rules"', '', s)
manifest.write_text(s)

# Branding.
strings = main / 'res/values/strings.xml'
if strings.exists():
    s = strings.read_text()
    s = re.sub(r'<string name="app_name">.*?</string>', '<string name="app_name">WINSUNG 98</string>', s)
    strings.write_text(s)

# Windows 98 / Classic is the default; XP and Vista remain separate native modes.
tm = main / 'java/rocks/gorjan/gokixp/theme/ThemeManager.kt'
s = tm.read_text()
s = s.replace('else -> WindowsXP // Default to XP if unknown', 'else -> WindowsClassic // WINSUNG default')
s = s.replace('prefs.getString(KEY_SELECTED_THEME, "Windows XP")', 'prefs.getString(KEY_SELECTED_THEME, "Windows Classic")')
tm.write_text(s)

# Remove Google Drive/account runtime paths from MainActivity while preserving local registry import/export.
ma = main / 'java/rocks/gorjan/gokixp/MainActivity.kt'
s = ma.read_text()
s = re.sub(r'^import rocks\.gorjan\.gokixp\.apps\.regedit\.GoogleDriveHelper\n', '', s, flags=re.M)
# Remove Google Play Services auth imports, but DO NOT remove com.google.gson.* used by local launcher state.
s = re.sub(r'^import com\.google\.android\.gms\..*\n', '', s, flags=re.M)
s = re.sub(r'\n\s*private lateinit var googleDriveHelper: GoogleDriveHelper\n', '\n', s)
s = re.sub(r'\n\s*// Google Sign-In launcher for Google Drive\n\s*private val googleSignInLauncher = registerForActivityResult\(ActivityResultContracts\.StartActivityForResult\(\)\) \{ result ->.*?\n\s*\}\n\n\s*// Sound system', '\n\n    // Sound system', s, flags=re.S)
s = re.sub(r'\n\s*// Auto-sync for Google Drive\n\s*private val autoSyncHandler.*?private var registryEditorAppInstance: RegistryEditorApp\? = null\n', '\n    private var registryEditorAppInstance: RegistryEditorApp? = null\n', s, flags=re.S)
s = re.sub(r'\n\s*// Initialize Google Drive helper\n.*?\n\s*// Initialize floating window manager', '\n\n        // Initialize floating window manager', s, flags=re.S)
s = re.sub(r'\n\s*onExportToGoogleDrive = \{ prefsToExport -> exportToGoogleDrive\(prefsToExport\) \},', '', s)
s = re.sub(r'\n\s*onImportFromGoogleDrive = \{ importFromGoogleDrive\(\) \},', '', s)
s = re.sub(r'\n\s*onAutoSyncChanged = \{ enabled -> handleAutoSyncChanged\(enabled\) \},', '', s)
s = re.sub(r'\n\s*getLastSyncTime = \{ preferences\.getSafeLong\(KEY_LAST_GOOGLE_DRIVE_SYNC, 0L\) \}', '', s)
s = re.sub(r'\n\s*private fun exportToGoogleDrive\(prefs: android\.content\.SharedPreferences\) \{.*?\n\s*private fun showDialerDialog\(\) \{', '\n\n    private fun showDialerDialog() {', s, flags=re.S)
# RegistryEditorApp cleanup is a no-op upstream; the local-only stripped variant does not expose it.\ns = s.replace('            regeditApp.cleanup()\\n', '')\n# Remove any remaining auto-sync call sites after the cloud functions were deleted.
s = re.sub(r'^\s*stopAutoSync\(\)\s*$', '        // WINSUNG private build: no cloud auto-sync', s, flags=re.M)
s = re.sub(r'^\s*startAutoSync\(\)\s*$', '            // WINSUNG private build: no cloud auto-sync', s, flags=re.M)
# Remote updater disabled in private build.
s = s.replace('        startUpdateChecker()', '        // WINSUNG private build: remote updater removed')
s = s.replace('        stopUpdateChecker()', '        // WINSUNG private build: no updater service')
s = re.sub(r'private fun checkForUpdates\(showCheckingNotification: Boolean = false\) \{.*?\n\s*private fun startUpdateChecker\(\) \{.*?\n\s*private fun stopUpdateChecker\(\) \{.*?\n\s*\}', '''private fun checkForUpdates(showCheckingNotification: Boolean = false) {
        if (showCheckingNotification) showNotification("Windows Update", "Updates are disabled in this private build")
    }

    private fun startUpdateChecker() { }
    private fun stopUpdateChecker() { }''', s, flags=re.S)
# No migration/export to the author's companion launcher.
s = s.replace('wasWindowsPhoneUser = WP8Migration.captureIfNeeded(this)', 'wasWindowsPhoneUser = false')
# Make every legacy fallback default Classic too.
s = s.replace('getString("selected_theme", "Windows XP") ?: "Windows XP"', 'getString("selected_theme", "Windows Classic") ?: "Windows Classic"')
# Factory-default Windows 98 desktop is solid classic teal. Patch the real
# loadSavedWallpaper() function specifically (there are several wallpaper-key
# lookups elsewhere in MainActivity).
wallpaper_pattern = re.compile(
    r'(private fun loadSavedWallpaper\(\) \{\s*\n\s*val prefs = getSharedPreferences\(PREFS_NAME, MODE_PRIVATE\)\s*\n\s*val \(pathKey, uriKey\) = getCurrentThemeWallpaperKeys\(\))'
)
wallpaper_insert = r'''\1

        if (themeManager.getSelectedTheme() is AppTheme.WindowsClassic) {
            val migrationKey = "winsung_classic_teal_default_v2"
            val existingPath = prefs.getString(KEY_WALLPAPER_CLASSIC_PATH, null)
            val existingUri = prefs.getString(KEY_WALLPAPER_CLASSIC_URI, null)

            // Migrate the inherited Jovanovski Classic default to WINSUNG teal once,
            // but preserve wallpapers the user actually chose.
            if (!prefs.getBoolean(migrationKey, false)) {
                if (existingUri == null &&
                    (existingPath == null || existingPath == "wallpapers/Windows ME (m).jpg")) {
                    prefs.edit {
                        remove(KEY_WALLPAPER_CLASSIC_PATH)
                        putBoolean(migrationKey, true)
                    }
                } else {
                    prefs.edit { putBoolean(migrationKey, true) }
                }
            }

            if (prefs.getString(KEY_WALLPAPER_CLASSIC_URI, null) == null &&
                prefs.getString(KEY_WALLPAPER_CLASSIC_PATH, null) == null) {
                val root = findViewById<android.widget.RelativeLayout>(R.id.main_background)
                root?.findViewWithTag<android.widget.ImageView>("wallpaper")?.let { root.removeView(it) }
                root?.setBackgroundColor(android.graphics.Color.rgb(0, 128, 128))
                return
            }
        }'''
s, wallpaper_count = wallpaper_pattern.subn(wallpaper_insert, s, count=1)
if wallpaper_count != 1:
    raise SystemExit(f'Could not patch loadSavedWallpaper safely (count={wallpaper_count})')
ma.write_text(s)

# Registry Editor: local import/export only; remove cloud-sync controls.
reg = main / 'java/rocks/gorjan/gokixp/apps/regedit/RegistryEditorApp.kt'
s = reg.read_text()
s = s.replace('    private val onExportToGoogleDrive: (SharedPreferences) -> Unit,\n', '')
s = s.replace('    private val onImportFromGoogleDrive: () -> Unit,\n', '')
s = s.replace('    private val onAutoSyncChanged: (Boolean) -> Unit,\n', '')
s = s.replace('    private val getLastSyncTime: () -> Long\n', '')
s = s.replace('    private var lastSyncTextView: TextView? = null\n', '')
s = s.replace('        val autoSyncCheckbox = contentView.findViewById<CheckBox>(R.id.auto_sync_checkbox)\n        lastSyncTextView = contentView.findViewById(R.id.last_sync_text)\n', '''        val autoSyncCheckbox = contentView.findViewById<CheckBox>(R.id.auto_sync_checkbox)
        val lastSyncTextView = contentView.findViewById<TextView>(R.id.last_sync_text)
        autoSyncCheckbox.visibility = View.GONE
        lastSyncTextView.visibility = View.GONE
''')
s = re.sub(r'\n\s*// Load auto-sync state\n.*?onAutoSyncChanged\(isChecked\)\n\s*\}', '', s, flags=re.S)
s = re.sub(r'\n\s*private fun updateLastSyncText\(\).*?\n\s*fun onSyncCompleted\(\) \{.*?\n\s*\}', '\n\n    fun onSyncCompleted() { }', s, flags=re.S)
start = s.index('    private fun showExportChoiceDialog')
end = s.index('    private fun showImportChoiceDialog', start)
s = s[:start] + '''    private fun showExportChoiceDialog(prefs: SharedPreferences) {
        onExportToLocalFile(prefs)
    }

''' + s[end:]
start = s.index('    private fun showImportChoiceDialog')
end = s.index('    fun cleanup()', start)
s = s[:start] + '''    private fun showImportChoiceDialog(prefs: SharedPreferences) {
        onImportFromLocalFile()
    }

''' + s[end:]
reg.write_text(s)

gdh = main / 'java/rocks/gorjan/gokixp/apps/regedit/GoogleDriveHelper.kt'
if gdh.exists():
    gdh.unlink()

print('WINSUNG source preparation complete')
