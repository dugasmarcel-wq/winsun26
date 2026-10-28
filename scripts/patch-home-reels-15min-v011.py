#!/usr/bin/env python3
"""Update v0.10 without changing the Direct Only navigation or app layout.

Home is 15 minutes per day. DM-shared Instagram Reel playback has its
own independent 15-minute allowance. YouTube Shorts stays at 60 seconds.
"""
from pathlib import Path
import sys

root=Path(sys.argv[1])
java=root/"app/src/main/java/dev/directonly"

def change(path, items):
    s=path.read_text()
    for old,new in items:
        occurrences=s.count(old)
        if occurrences!=1:
            raise RuntimeError(f"Expected one match in {path.name}, found {occurrences}: {old[:120]!r}")
        s=s.replace(old,new,1)
    path.write_text(s)

# Existing Home allowance, same persistence and midnight-reset behaviour.
change(java/"HomeBudget.java",[
    ("DAILY_MS = 25L * 60L * 1000L", "DAILY_MS = 15L * 60L * 1000L"),
    ("extra twenty-five minutes", "extra fifteen minutes"),
])

# Separate allowance; a new class, NOT a new screen or navigation item.
base=(java/"HomeBudget.java").read_text()
reels=(base.replace("HomeBudget", "ReelsBudget")
        .replace("Home", "Reels")
        .replace("home_allowance_v1", "instagram_reels_allowance_v1"))
assert 'DAILY_MS = 15L * 60L * 1000L' in reels
assert "instagram_reels_allowance_v1" in reels
(java/"ReelsBudget.java").write_text(reels)

activity=java/"MainActivity.java"
change(activity,[
    ("    private HomeBudget homeBudget;\n    private Button homeButton;",
     """    private HomeBudget homeBudget;
    private ReelsBudget reelsBudget;
    private Button homeButton;
    private TextView reelTimerHint;
    private boolean inlineVideoOpen;"""),
    ("""                updateHomeButton();
            }
            usageHandler.postDelayed(this, 250);""",
     """                updateHomeButton();
            }
            if (reelsBudget != null) {
                long remaining = reelsBudget.remainingMillis();
                if (reelsBudget.isRunning() && remaining == 0L) {
                    reelsBudget.stop();
                    if (reel != null) closeReel();
                    inlineVideoOpen = false;
                    if (inlineShield != null) inlineShield.setVisibility(View.GONE);
                    if (messages != null) messages.loadUrl(UrlPolicy.INBOX);
                    Toast.makeText(MainActivity.this,
                        "15 minutes of Reels used. Resets at midnight.",
                        Toast.LENGTH_LONG).show();
                }
                updateReelHint();
            }
            usageHandler.postDelayed(this, 250);"""),
    ("        homeBudget = new HomeBudget(this);",
     "        homeBudget = new HomeBudget(this);\n        reelsBudget = new ReelsBudget(this);"),
    ('button("Home 25:00", v -> enterHome())',
     'button("Home 15:00", v -> enterHome())'),
    ('"Twenty-five minutes of Home feed browsing per local calendar day, resetting at midnight. "',
     '"Fifteen minutes of Home feed browsing per local calendar day, resetting at midnight. "'),
    ('"The same Accessibility permission blocks native Instagram and limits YouTube Shorts to one minute per day. "',
     '"Instagram Reels shared in DMs have a separate fifteen-minute daily viewing limit. " +\n                             "The same Accessibility permission blocks native Instagram and limits YouTube Shorts to one minute per day. "'),
    ("""    private void showSingleReel(String url) {
        if (UrlPolicy.classify(url) != UrlPolicy.Destination.SINGLE_REEL) return;
        if (reel != null) closeReel();
        activeReel = url;""",
     """    private void showSingleReel(String url) {
        if (UrlPolicy.classify(url) != UrlPolicy.Destination.SINGLE_REEL) return;
        if (!foreground || reelsBudget.remainingMillis() <= 0L) {
            Toast.makeText(this, "15-minute Reels allowance used today.", Toast.LENGTH_LONG).show();
            return;
        }
        if (reel != null) closeReel();
        reelsBudget.begin();
        activeReel = url;"""),
    ('        TextView hint = label("One Reel only", 12, grey);\n        toolbar.addView(hint, new LinearLayout.LayoutParams(0, dp(52), 1));',
     '        reelTimerHint = label("One Reel · 15:00", 12, grey);\n        toolbar.addView(reelTimerHint, new LinearLayout.LayoutParams(0, dp(52), 1));\n        updateReelHint();'),
    ("""        reel.destroy();
        reel = null;
        activeReel = null;
    }""",
     """        reel.destroy();
        reel = null;
        activeReel = null;
        reelTimerHint = null;
        if (!inlineVideoOpen && reelsBudget != null) reelsBudget.stop();
    }"""),
    ("""                if (inlineShield != null && reel == null) {
                    inlineShield.setVisibility(isOpen ? View.VISIBLE : View.GONE);
                }""",
     """                if (inlineShield != null && reel == null) {
                    if (isOpen && (!foreground || !reelsBudget.begin())) {
                        inlineVideoOpen = false;
                        inlineShield.setVisibility(View.GONE);
                        messages.loadUrl(UrlPolicy.INBOX);
                        Toast.makeText(MainActivity.this,
                            "15-minute Reels allowance used today.", Toast.LENGTH_LONG).show();
                    } else {
                        inlineVideoOpen = isOpen;
                        if (!isOpen) reelsBudget.stop();
                        inlineShield.setVisibility(isOpen ? View.VISIBLE : View.GONE);
                    }
                }"""),
    ("""        updateHomeButton();
        if (getIntent() != null && ACTION_SHOW_INBOX.equals(getIntent().getAction())) {""",
     """        updateHomeButton();
        if ((reel != null || inlineVideoOpen) && !reelsBudget.begin()) {
            if (reel != null) closeReel();
            inlineVideoOpen = false;
            if (inlineShield != null) inlineShield.setVisibility(View.GONE);
            goInbox();
        }
        if (getIntent() != null && ACTION_SHOW_INBOX.equals(getIntent().getAction())) {"""),
    ("""        if (homeBudget != null) homeBudget.stop();
        super.onPause();""",
     """        if (homeBudget != null) homeBudget.stop();
        if (reelsBudget != null) reelsBudget.stop();
        super.onPause();"""),
    ("""        if (reel != null) closeReel();
        if (inlineShield != null) inlineShield.setVisibility(View.GONE);
        updateHomeButton();""",
     """        if (reel != null) closeReel();
        inlineVideoOpen = false;
        if (reelsBudget != null) reelsBudget.stop();
        if (inlineShield != null) inlineShield.setVisibility(View.GONE);
        updateHomeButton();"""),
    ("""    private void goInbox() {
        if (homeBudget != null) homeBudget.stop();""",
     """    private void goInbox() {
        inlineVideoOpen = false;
        if (reelsBudget != null && reel == null) reelsBudget.stop();
        if (homeBudget != null) homeBudget.stop();"""),
    ("""    private void enableMediaAudio() {""",
     """    private void updateReelHint() {
        if (reelTimerHint == null || reelsBudget == null) return;
        long seconds = (reelsBudget.remainingMillis() + 999L) / 1000L;
        reelTimerHint.setText(String.format(Locale.ROOT,
            "One Reel · %d:%02d", seconds / 60, seconds % 60));
    }

    private void enableMediaAudio() {"""),
    ("""        if (reel != null) { closeReel(); return; }""",
     """        if (reel != null) { closeReel(); return; }
        if (inlineVideoOpen) {
            inlineVideoOpen = false;
            if (reelsBudget != null) reelsBudget.stop();
            if (inlineShield != null) inlineShield.setVisibility(View.GONE);
            goInbox();
            return;
        }"""),
])

# The inline viewer already has a Back to chat toolbar: stop its timer when that
# native control is used (the JS dismissal callback may otherwise arrive later).
change(activity,[
    ("""            inlineShield.setVisibility(View.GONE);
            String chat = messages.getUrl();""",
     """            inlineShield.setVisibility(View.GONE);
            inlineVideoOpen = false;
            reelsBudget.stop();
            String chat = messages.getUrl();"""),
])
change(root/"app/build.gradle",[
    ("versionCode 10", "versionCode 11"),
    ("versionName '0.10.0'", "versionName '0.11.0'"),
])

home=(java/"HomeBudget.java").read_text()
main=activity.read_text()
youtube=(java/"ShortsBudget.java").read_text()
service=(java/"InstagramBlockService.java").read_text()
assert "DAILY_MS = 15L * 60L * 1000L" in home
assert 'button("Home 15:00"' in main
assert 'button("Reels"' not in main
assert 'ReelsActivity' not in main
assert not (java/"ReelsActivity.java").exists()
assert "DAILY_MS = 15L * 60L * 1000L" in (java/"ReelsBudget.java").read_text()
assert "reelsBudget.begin()" in main and "reelsBudget.stop()" in main
assert "inlineVideoOpen" in main
assert "DAILY_MS = 60_000L" in youtube
assert "shortsBudget.remainingMillis()" in service
assert 'toolbar.addView(button("Reload"' in main
print("v0.11 checks passed: original UI; Home 15 min; shared Reels 15 min; YouTube Shorts 60 sec.")
