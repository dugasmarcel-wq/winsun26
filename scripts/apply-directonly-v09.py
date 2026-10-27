#!/usr/bin/env python3
"""Minimal correction from the v0.6 Direct Only source. No extra Instagram screens."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
java = root / "app/src/main/java/dev/directonly"

def edit(file, operations):
    value = file.read_text()
    for old, new in operations:
        occurrences = value.count(old)
        if occurrences != 1:
            raise RuntimeError(f"{file.name}: expected one occurrence, found {occurrences}: {old[:100]!r}")
        value = value.replace(old, new, 1)
    file.write_text(value)

edit(java / "HomeBudget.java", [
    ("DAILY_MS = 5L * 60L * 1000L", "DAILY_MS = 25L * 60L * 1000L"),
    ("extra five minutes", "extra twenty-five minutes"),
])
edit(java / "MainActivity.java", [
    ('button("Home 5:00", v -> enterHome())',
     'button("Home 25:00", v -> enterHome())'),
    ('"Five minutes of Home feed browsing per local calendar day, resetting at midnight. "',
     '"Twenty-five minutes of Home feed browsing per local calendar day, resetting at midnight. "'),
    ('"The same Accessibility permission blocks the native Instagram interface and YouTube Shorts. "',
     '"The same Accessibility permission blocks native Instagram and limits YouTube Shorts to ten per day. "'),
    ('"Direct Only checks Shorts screen controls; YouTube updates may bypass the blocker. "',
     '"Shorts detection depends on YouTube accessibility signals and may miss some transitions. "'),
])
(java / "ShortsBudget.java").write_text("""package dev.directonly;

import android.content.Context;
import android.content.SharedPreferences;
import java.time.LocalDate;

/** Persistent ten-Short daily cap with phone-local midnight reset. */
public final class ShortsBudget {
    private final SharedPreferences preferences;
    public ShortsBudget(Context context) {
        preferences = context.getApplicationContext()
                .getSharedPreferences("youtube_shorts_daily_v1", Context.MODE_PRIVATE);
    }
    private void resetOnNewDay() {
        String saved = preferences.getString("day", "");
        String today = LocalDate.now().toString();
        // Rolling the phone clock back cannot grant another day's allowance.
        if (saved.isEmpty() || today.compareTo(saved) > 0) {
            preferences.edit().putString("day", today).putInt("used", 0).commit();
        }
    }
    public synchronized int remaining() {
        resetOnNewDay();
        return Math.max(0, 10 - preferences.getInt("used", 0));
    }
    public synchronized boolean consume() {
        resetOnNewDay();
        int used = preferences.getInt("used", 0);
        return used < 10 && preferences.edit().putInt("used", used + 1).commit();
    }
}
""")
service = java / "InstagramBlockService.java"
edit(service, [
    ("    private long lastYoutubeEventAt;",
     """    private long lastYoutubeEventAt;
    private ShortsBudget shortsBudget;
    private boolean shortsOpen;
    private long lastCountedShortAt;
    private int lastScrollIndex = -1;"""),
    ("""        if (!YOUTUBE_PACKAGE.equals(pkg)) return;
        lastYoutubeEventAt = SystemClock.elapsedRealtime();""",
     """        if (!YOUTUBE_PACKAGE.equals(pkg)) {
            if (type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
                type == AccessibilityEvent.TYPE_WINDOWS_CHANGED) shortsOpen = false;
            return;
        }
        if (shortsBudget == null) shortsBudget = new ShortsBudget(this);
        lastYoutubeEventAt = SystemClock.elapsedRealtime();"""),
    ("""                if (clickedShorts(source, event.getText())) {
                    blockShorts();
                    return;
                }""",
     """                if (clickedShorts(source, event.getText())) {
                    if (shortsBudget.remaining() == 0) blockShorts();
                    else handler.postDelayed(verifyShorts, 250);
                    return;
                }"""),
    ("""            if (ShortsSignals.playerWindow(event.getClassName())) {
                blockShorts();
                return;
            }""",
     """            if (ShortsSignals.playerWindow(event.getClassName())) {
                onShortsVisible();
                return;
            }"""),
    ("""        if (type == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED ||
                type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||""",
     """        if (type == AccessibilityEvent.TYPE_VIEW_SCROLLED && shortsOpen) {
            onShortsScroll(event);
        }
        if (type == AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED ||
                type == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||"""),
    ("""            if (root != null) root.recycle();
            return;
        }
        boolean found = false;""",
     """            if (root != null) root.recycle();
            shortsOpen = false;
            return;
        }
        boolean found = false;"""),
    ("""        if (found) blockShorts();
        else if (SystemClock.elapsedRealtime() - lastShortsBlockAt > 1800) consecutiveShortsBacks = 0;
    }

    private void blockShorts() {""",
     """        if (found) onShortsVisible();
        else if (SystemClock.elapsedRealtime() - lastCountedShortAt > 3500) {
            // Wait before treating a temporarily incomplete accessibility tree as an exit.
            shortsOpen = false;
            if (SystemClock.elapsedRealtime() - lastShortsBlockAt > 1800)
                consecutiveShortsBacks = 0;
        }
    }

    private void onShortsVisible() {
        if (shortsBudget == null) shortsBudget = new ShortsBudget(this);
        if (shortsOpen) return; // repeated redraws are NOT new Shorts
        shortsOpen = true;
        lastCountedShortAt = SystemClock.elapsedRealtime();
        lastScrollIndex = -1;
        if (!shortsBudget.consume()) blockShorts();
    }

    private void onShortsScroll(AccessibilityEvent event) {
        long now = SystemClock.elapsedRealtime();
        if (now - lastCountedShortAt < 900) return;
        AccessibilityNodeInfo node = event.getSource();
        boolean isShortsPager = false;
        if (node != null) {
            try {
                String id = String.valueOf(node.getViewIdResourceName())
                    .toLowerCase(java.util.Locale.ROOT);
                String cls = String.valueOf(node.getClassName())
                    .toLowerCase(java.util.Locale.ROOT);
                isShortsPager = id.contains("shorts") || id.contains("reel") ||
                    cls.contains("viewpager");
            } finally {
                node.recycle();
            }
        }
        int next = event.getToIndex();
        boolean moved = next >= 0 && next != lastScrollIndex;
        if (!isShortsPager || !moved) return;
        lastScrollIndex = next;
        lastCountedShortAt = now;
        if (shortsBudget == null) shortsBudget = new ShortsBudget(this);
        if (!shortsBudget.consume()) blockShorts();
    }

    private void blockShorts() {"""),
    ("""    private void blockShorts() {
        long now = SystemClock.elapsedRealtime();""",
     """    private void blockShorts() {
        shortsOpen = false;
        long now = SystemClock.elapsedRealtime();"""),
])
edit(root / "app/build.gradle", [
    ("versionCode 6", "versionCode 9"),
    ("versionName '0.6.0'", "versionName '0.9.0'"),
])

activity = (java / "MainActivity.java").read_text()
assert 'button("Home 25:00"' in activity
assert 'toolbar.addView(button("Reload"' in activity
assert 'button("Reels"' not in activity
assert 'ReelsActivity' not in activity
assert 'ReelsBudget' not in activity
assert not (java / "ReelsActivity.java").exists()
assert not (java / "ReelsBudget.java").exists()
assert "DAILY_MS = 25L * 60L * 1000L" in (java / "HomeBudget.java").read_text()
assert "shortsBudget.consume()" in service.read_text()
print("v0.9 patch checks passed: original UI, Home 25:00, ten Shorts, no extra Reels interface.")
