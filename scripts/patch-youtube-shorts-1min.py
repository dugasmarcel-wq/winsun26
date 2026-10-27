#!/usr/bin/env python3
"""Only replace Direct Only v0.9's YouTube Shorts count limit with 60 seconds/day."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
java = root / "app/src/main/java/dev/directonly"

def replace_exact(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError("%s expected once, found %s: %r" % (label, n, old[:100]))
    return text.replace(old, new, 1)

budget_path = java / "ShortsBudget.java"
assert budget_path.exists()
budget_path.write_text("""package dev.directonly;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;
import java.time.LocalDate;

/**
 * Daily 60-second foreground YouTube Shorts viewing allowance.
 * Time persists immediately, pauses away from Shorts and resets at local midnight.
 */
public final class ShortsBudget {
    public static final long DAILY_MS = 60_000L;
    private final SharedPreferences prefs;
    private boolean running;
    private long lastElapsed;

    public ShortsBudget(Context context) {
        prefs = context.getApplicationContext()
                .getSharedPreferences("youtube_shorts_time_v1", Context.MODE_PRIVATE);
        resetForDay();
    }

    private void resetForDay() {
        String today = LocalDate.now().toString();
        String previous = prefs.getString("local_day", "");
        // Never grant additional time when the phone date is rolled backwards.
        if (previous.isEmpty() || today.compareTo(previous) > 0) {
            prefs.edit().putString("local_day", today).putLong("used_ms", 0L).commit();
            if (running) lastElapsed = SystemClock.elapsedRealtime();
        }
    }

    private void accrue() {
        resetForDay();
        if (!running) return;
        long now = SystemClock.elapsedRealtime();
        long delta = now >= lastElapsed ? now - lastElapsed : 0L;
        lastElapsed = now;
        if (delta > 0L) {
            long used = Math.min(DAILY_MS, prefs.getLong("used_ms", 0L) + delta);
            prefs.edit().putLong("used_ms", used).commit();
        }
    }

    public synchronized long remainingMillis() {
        accrue();
        return Math.max(0L, DAILY_MS - prefs.getLong("used_ms", 0L));
    }

    public synchronized boolean begin() {
        if (remainingMillis() <= 0L) return false;
        if (!running) {
            running = true;
            lastElapsed = SystemClock.elapsedRealtime();
        }
        return true;
    }

    public synchronized void stop() {
        accrue();
        running = false;
    }
}
""")

service = java / "InstagramBlockService.java"
code = service.read_text()
code = replace_exact(code,
    "    private long lastCountedShortAt;\n    private int lastScrollIndex = -1;",
    """    private long lastShortsEvidenceAt;
    private final Runnable shortsTimeTick = new Runnable() {
        @Override public void run() {
            if (!shortsOpen || shortsBudget == null) return;
            android.os.PowerManager pm =
                (android.os.PowerManager) getSystemService(POWER_SERVICE);
            if (pm != null && !pm.isInteractive()) {
                stopShortsSession();
                return;
            }
            if (shortsBudget.remainingMillis() == 0L) {
                blockShorts();
                return;
            }
            checkShortsTree();
            if (shortsOpen) handler.postDelayed(this, 250L);
        }
    };""", "shorts fields")
code = replace_exact(code,
    """                type == AccessibilityEvent.TYPE_WINDOWS_CHANGED) shortsOpen = false;""",
    """                type == AccessibilityEvent.TYPE_WINDOWS_CHANGED) stopShortsSession();""",
    "leave YouTube")
code = replace_exact(code,
    "if (shortsBudget.remaining() == 0) blockShorts();",
    "if (shortsBudget.remainingMillis() == 0L) blockShorts();",
    "limit on Shorts tab click")
code = replace_exact(code,
    """        if (type == AccessibilityEvent.TYPE_VIEW_SCROLLED && shortsOpen) {
            onShortsScroll(event);
        }
""", "", "remove count-per-scroll")
code = replace_exact(code,
    """            shortsOpen = false;
            return;
        }
        boolean found = false;""",
    """            stopShortsSession();
            return;
        }
        boolean found = false;""",
    "stop when another app is active")
start = code.index("        if (found) onShortsVisible();")
end = code.index("    private void blockShorts() {", start)
code = code[:start] + """        if (found) onShortsVisible();
        else if (shortsOpen && SystemClock.elapsedRealtime() - lastShortsEvidenceAt > 1800L)
            stopShortsSession();
    }

    private void onShortsVisible() {
        if (shortsBudget == null) shortsBudget = new ShortsBudget(this);
        lastShortsEvidenceAt = SystemClock.elapsedRealtime();
        if (shortsOpen) return;
        if (!shortsBudget.begin()) {
            blockShorts();
            return;
        }
        shortsOpen = true;
        handler.removeCallbacks(shortsTimeTick);
        handler.postDelayed(shortsTimeTick, 250L);
    }

    private void stopShortsSession() {
        shortsOpen = false;
        handler.removeCallbacks(shortsTimeTick);
        if (shortsBudget != null) shortsBudget.stop();
    }

""" + code[end:]
code = replace_exact(code,
    """    private void blockShorts() {
        shortsOpen = false;
        long now = SystemClock.elapsedRealtime();""",
    """    private void blockShorts() {
        stopShortsSession();
        // Exiting to Home prevents Back from revealing another Short.
        if (shortsBudget != null && shortsBudget.remainingMillis() == 0L) {
            performGlobalAction(GLOBAL_ACTION_HOME);
            return;
        }
        long now = SystemClock.elapsedRealtime();""", "block after 60 seconds")
code = replace_exact(code,
    """    @Override public void onInterrupt() { handler.removeCallbacks(verifyShorts); }
    @Override public void onDestroy() { handler.removeCallbacks(verifyShorts); super.onDestroy(); }""",
    """    @Override public void onInterrupt() {
        handler.removeCallbacks(verifyShorts);
        stopShortsSession();
    }
    @Override public void onDestroy() {
        handler.removeCallbacks(verifyShorts);
        stopShortsSession();
        super.onDestroy();
    }""", "stop on accessibility shutdown")
service.write_text(code)

main_path = java / "MainActivity.java"
main = main_path.read_text()
main = replace_exact(main,
    "limits YouTube Shorts to ten per day.",
    "limits YouTube Shorts to one minute per day.",
    "description")
main_path.write_text(main)

gradle_path = root / "app/build.gradle"
gradle = gradle_path.read_text()
gradle = replace_exact(gradle, "versionCode 9", "versionCode 10", "version code")
gradle = replace_exact(gradle, "versionName '0.9.0'", "versionName '0.10.0'", "version name")
gradle_path.write_text(gradle)

assert 'button("Home 25:00"' in main
assert 'toolbar.addView(button("Reload"' in main
assert 'button("Reels"' not in main
assert 'ReelsActivity' not in main and 'ReelsBudget' not in main
assert not (java / "ReelsActivity.java").exists()
assert not (java / "ReelsBudget.java").exists()
assert "DAILY_MS = 25L * 60L * 1000L" in (java / "HomeBudget.java").read_text()
assert "DAILY_MS = 60_000L" in budget_path.read_text()
assert "onShortsScroll" not in code
assert "shortsBudget.consume()" not in code
assert "shortsTimeTick" in code and "shortsBudget.remainingMillis()" in code
assert "stopShortsSession();" in code
print("v0.10 checks passed: unchanged UI, Home 25:00, Shorts 60 sec per local day.")
