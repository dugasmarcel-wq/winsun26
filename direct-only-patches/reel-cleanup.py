from pathlib import Path
p = Path("direct-only-project/app/src/main/java/dev/directonly/MainActivity.java")
s = p.read_text()
old = """        reelSurface.removeView(reel);
        reel.destroy();"""
new = """        ViewGroup parent = (ViewGroup) reel.getParent();
        if (parent != null) parent.removeView(reel);
        reelSurface.removeAllViews();
        reel.destroy();"""
if old not in s: raise RuntimeError("Expected Reel cleanup not found")
p.write_text(s.replace(old, new))

# Native playback control must be able to start the selected video in a WebView.
s = p.read_text()
s = s.replace('s.setMediaPlaybackRequiresUserGesture(true);', 's.setMediaPlaybackRequiresUserGesture(false);')
p.write_text(s)
