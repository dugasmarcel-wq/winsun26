package rocks.gorjan.gokixp.winsung

import android.content.ComponentName
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Shader
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.graphics.drawable.GradientDrawable
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.BatteryManager
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.animation.DecelerateInterpolator
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.RelativeLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import rocks.gorjan.gokixp.MainActivity
import rocks.gorjan.gokixp.NotificationListenerService
import rocks.gorjan.gokixp.R
import rocks.gorjan.gokixp.theme.AppTheme
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors
import javax.net.ssl.HttpsURLConnection
import kotlin.math.abs
import kotlin.math.roundToInt

internal fun Context.wdp(v: Int): Int = (v * resources.displayMetrics.density).roundToInt()

private const val FACE = 0xffc0c0c0.toInt()
private const val DESKTOP_TEAL = 0xff008080.toInt()
private const val NAVY = 0xff000080.toInt()
private const val TITLE_BLUE = 0xff1084d0.toInt()

private class ClassicBevelDrawable(
    private val fill: Int = FACE,
    private val sunken: Boolean = false,
    private val border: Int = 2
) : Drawable() {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    override fun draw(c: Canvas) {
        val b = bounds
        p.color = fill
        c.drawRect(b.left.toFloat(), b.top.toFloat(), b.right.toFloat(), b.bottom.toFloat(), p)
        val hi = if (sunken) Color.rgb(64, 64, 64) else Color.WHITE
        val lo = if (sunken) Color.WHITE else Color.rgb(64, 64, 64)
        val midHi = if (sunken) Color.rgb(128, 128, 128) else Color.rgb(223, 223, 223)
        val midLo = if (sunken) Color.rgb(223, 223, 223) else Color.rgb(128, 128, 128)
        val n = border.coerceAtLeast(1)
        for (i in 0 until n) {
            p.color = if (i == 0) hi else midHi
            c.drawRect((b.left + i).toFloat(), (b.top + i).toFloat(), (b.right - i).toFloat(), (b.top + i + 1).toFloat(), p)
            c.drawRect((b.left + i).toFloat(), (b.top + i).toFloat(), (b.left + i + 1).toFloat(), (b.bottom - i).toFloat(), p)
            p.color = if (i == 0) lo else midLo
            c.drawRect((b.left + i).toFloat(), (b.bottom - i - 1).toFloat(), (b.right - i).toFloat(), (b.bottom - i).toFloat(), p)
            c.drawRect((b.right - i - 1).toFloat(), (b.top + i).toFloat(), (b.right - i).toFloat(), (b.bottom - i).toFloat(), p)
        }
    }
    override fun setAlpha(alpha: Int) { p.alpha = alpha }
    override fun setColorFilter(colorFilter: android.graphics.ColorFilter?) { p.colorFilter = colorFilter }
    @Deprecated("Deprecated in Java") override fun getOpacity(): Int = PixelFormat.OPAQUE
}

private fun raised(fill: Int = FACE): Drawable = ClassicBevelDrawable(fill, false)
private fun inset(fill: Int = Color.WHITE): Drawable = ClassicBevelDrawable(fill, true)
private fun blueBar(): GradientDrawable = GradientDrawable(
    GradientDrawable.Orientation.LEFT_RIGHT,
    intArrayOf(NAVY, TITLE_BLUE)
)

private fun assetDrawable(context: Context, path: String): Drawable? = try {
    context.assets.open(path).use { Drawable.createFromStream(it, path) }
} catch (_: Exception) { null }

private fun TextView.classicText(size: Float = 10f, color: Int = Color.BLACK, bold: Boolean = false): TextView = apply {
    textSize = size
    setTextColor(color)
    typeface = Typeface.create(Typeface.SANS_SERIF, if (bold) Typeface.BOLD else Typeface.NORMAL)
    includeFontPadding = false
}

private fun classicButton(context: Context, label: String, action: () -> Unit): TextView = TextView(context).apply {
    text = label
    classicText(10f, Color.BLACK, false)
    gravity = Gravity.CENTER
    background = raised()
    isClickable = true
    isFocusable = true
    setPadding(context.wdp(6), context.wdp(3), context.wdp(6), context.wdp(3))
    setOnClickListener { action() }
}

private fun titleBar(context: Context, title: String, iconPath: String? = null): LinearLayout = LinearLayout(context).apply {
    orientation = LinearLayout.HORIZONTAL
    gravity = Gravity.CENTER_VERTICAL
    setPadding(context.wdp(3), context.wdp(2), context.wdp(3), context.wdp(2))
    background = blueBar()
    if (iconPath != null) addView(ImageView(context).apply {
        scaleType = ImageView.ScaleType.CENTER_INSIDE
        setImageDrawable(assetDrawable(context, iconPath))
    }, LinearLayout.LayoutParams(context.wdp(16), context.wdp(16)).apply { marginEnd = context.wdp(4) })
    addView(TextView(context).apply {
        text = title
        classicText(11f, Color.WHITE, true)
        gravity = Gravity.CENTER_VERTICAL
    }, LinearLayout.LayoutParams(0, context.wdp(18), 1f))
}

private fun addTopInset(view: View, content: View, left: Int, top: Int, right: Int, bottom: Int) {
    view.post {
        val inset = view.rootWindowInsets?.systemWindowInsetTop ?: 0
        content.setPadding(left, top + inset, right, bottom)
    }
}

open class SwipePageFrame(context: Context, private val onSwipe: (Int) -> Unit) : FrameLayout(context) {
    private var downX = 0f
    private var downY = 0f
    private var intercepting = false
    override fun onInterceptTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { downX = e.x; downY = e.y; intercepting = false }
            MotionEvent.ACTION_MOVE -> {
                val dx = e.x - downX
                val dy = e.y - downY
                if (abs(dx) > context.wdp(24) && abs(dx) > abs(dy) * 1.35f) {
                    intercepting = true
                    return true
                }
            }
        }
        return false
    }
    override fun onTouchEvent(e: MotionEvent): Boolean {
        if (e.actionMasked == MotionEvent.ACTION_DOWN) { downX = e.x; downY = e.y; return true }
        if (e.actionMasked == MotionEvent.ACTION_UP) {
            val dx = e.x - downX
            val dy = e.y - downY
            if ((intercepting || abs(dx) > context.wdp(58)) && abs(dx) > abs(dy)) onSwipe(if (dx > 0) -1 else 1)
            intercepting = false
            return true
        }
        if (e.actionMasked == MotionEvent.ACTION_CANCEL) intercepting = false
        return true
    }
}

data class FixedApp(val label: String, val packages: List<String>, val asset: String)
val FIXED_APPS = listOf(
    FixedApp("Phone", listOf("com.samsung.android.dialer", "com.google.android.dialer"), "custom_icons_98/Phone.webp"),
    FixedApp("Signal", listOf("org.thoughtcrime.securesms"), "custom_icons_98/accessibility_window_signal.webp"),
    FixedApp("Firefox", listOf("org.mozilla.firefox"), "custom_icons/Internet Explorer 6.webp"),
    FixedApp("WhatsApp", listOf("com.whatsapp"), "custom_icons_98/WhatsApp.webp"),
    FixedApp("YouTube Music", listOf("com.google.android.apps.youtube.music"), "custom_icons_programs/YouTube.webp")
)

class QuickGlancePage(
    private val activity: MainActivity,
    onSwipe: (Int) -> Unit,
    private val openUrl: (String) -> Unit,
    private val openCalendar: () -> Unit,
    private val openMedia: () -> Unit
) : SwipePageFrame(activity, onSwipe) {
    private val ui = Handler(Looper.getMainLooper())
    private val executor = Executors.newSingleThreadExecutor()
    private val news = LinearLayout(activity)
    private val clock = TextView(activity)
    private val date = TextView(activity)
    private val battery = TextView(activity)
    private var lastLoad = 0L
    private var loading = false
    private val tick = object : Runnable {
        override fun run() { updateHeader(); ui.postDelayed(this, 1000L) }
    }

    init {
        setBackgroundColor(Color.rgb(212, 208, 200))
        val scroll = ScrollView(activity).apply { isFillViewport = true; isVerticalScrollBarEnabled = true }
        val root = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        addView(scroll, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        scroll.addView(root, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        addTopInset(this, root, activity.wdp(10), activity.wdp(8), activity.wdp(10), activity.wdp(10))

        val hero = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(activity.wdp(8), activity.wdp(7), activity.wdp(8), activity.wdp(7))
            background = blueBar()
        }
        val left = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        left.addView(TextView(activity).apply { text = "WINSUNG 98  •  QUICK GLANCE"; classicText(8.5f, Color.rgb(220, 230, 255), true) })
        left.addView(date.apply { classicText(18f, Color.WHITE, false) })
        hero.addView(left, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
        hero.addView(clock.apply { classicText(21f, Color.WHITE, false); gravity = Gravity.END })
        root.addView(hero, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(62)))

        val glance = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, activity.wdp(7), 0, activity.wdp(7)) }
        glance.addView(glanceCard("Calendar", "Open", "custom_icons_98/calendar-0.webp", openCalendar), LinearLayout.LayoutParams(0, activity.wdp(62), 1f))
        glance.addView(glanceCard("Media", "Controls", "custom_icons_98/media_player-0.webp", openMedia), LinearLayout.LayoutParams(0, activity.wdp(62), 1f).apply { marginStart = activity.wdp(5); marginEnd = activity.wdp(5) })
        glance.addView(LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; background = raised(); setPadding(activity.wdp(6), 0, activity.wdp(5), 0)
            addView(ImageView(activity).apply { setImageDrawable(assetDrawable(activity, "custom_icons_98/computer_sound-0.webp")); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LinearLayout.LayoutParams(activity.wdp(26), activity.wdp(26)).apply { marginEnd = activity.wdp(4) })
            addView(LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; addView(TextView(activity).apply { text = "Battery"; classicText(8.5f, Color.DKGRAY) }); addView(battery.apply { classicText(15f, NAVY) }) })
        }, LinearLayout.LayoutParams(0, activity.wdp(62), 1f))
        root.addView(glance)

        root.addView(section("Top stories", news, true))
        val sources = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL }
        sources.addView(classicButton(activity, "Google News") { openUrl("https://news.google.com/") }, LinearLayout.LayoutParams(0, activity.wdp(35), 1f))
        sources.addView(classicButton(activity, "Reuters") { openUrl("https://www.reuters.com/") }, LinearLayout.LayoutParams(0, activity.wdp(35), 1f).apply { marginStart = activity.wdp(4); marginEnd = activity.wdp(4) })
        sources.addView(classicButton(activity, "AP") { openUrl("https://apnews.com/") }, LinearLayout.LayoutParams(0, activity.wdp(35), 1f))
        root.addView(section("News sources", sources, false), LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = activity.wdp(7) })
        showMessage("Loading headlines...")
        updateHeader()
    }

    private fun glanceCard(a: String, b: String, icon: String, action: () -> Unit) = LinearLayout(activity).apply {
        orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; background = raised(); isClickable = true; setOnClickListener { action() }; setPadding(activity.wdp(6), 0, activity.wdp(5), 0)
        addView(ImageView(activity).apply { setImageDrawable(assetDrawable(activity, icon)); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LinearLayout.LayoutParams(activity.wdp(28), activity.wdp(28)).apply { marginEnd = activity.wdp(4) })
        addView(LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; addView(TextView(activity).apply { text = a; classicText(8.5f, Color.DKGRAY) }); addView(TextView(activity).apply { text = b; classicText(14f, NAVY) }) })
    }

    private fun section(title: String, body: View, refresh: Boolean): View = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL; background = raised(); setPadding(activity.wdp(2), activity.wdp(2), activity.wdp(2), activity.wdp(2))
        val bar = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; background = blueBar(); setPadding(activity.wdp(6), 0, activity.wdp(4), 0) }
        bar.addView(TextView(activity).apply { text = title; classicText(10.5f, Color.WHITE, true) }, LinearLayout.LayoutParams(0, activity.wdp(24), 1f))
        if (refresh) bar.addView(classicButton(activity, "Refresh") { loadNews(true) }, LinearLayout.LayoutParams(activity.wdp(70), activity.wdp(20)))
        addView(bar, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(27)))
        addView(LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; setPadding(activity.wdp(6), activity.wdp(6), activity.wdp(6), activity.wdp(6)); addView(body) })
    }

    fun shown() { ui.removeCallbacks(tick); ui.post(tick); if (System.currentTimeMillis() - lastLoad > 15 * 60_000L) loadNews(false) }
    fun hidden() { ui.removeCallbacks(tick) }

    private fun updateHeader() {
        val now = Date()
        date.text = SimpleDateFormat("EEEE, MMMM d", Locale.US).format(now)
        clock.text = SimpleDateFormat("h:mm:ss a", Locale.US).format(now)
        val bm = activity.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val p = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        battery.text = if (p in 0..100) "$p%" else "--%"
    }

    private fun showMessage(t: String) {
        news.removeAllViews()
        news.addView(TextView(activity).apply { text = t; classicText(10f, Color.DKGRAY); gravity = Gravity.CENTER; setPadding(activity.wdp(8), activity.wdp(20), activity.wdp(8), activity.wdp(20)) })
    }

    private fun loadNews(force: Boolean) {
        if (loading || (!force && System.currentTimeMillis() - lastLoad < 15 * 60_000L)) return
        loading = true
        showMessage("Loading headlines...")
        executor.execute {
            try {
                val endpoint = "https://api.gdeltproject.org/api/v2/doc/doc?query=sourcelang%3Aenglish&mode=ArtList&maxrecords=30&format=json&sort=HybridRel"
                val c = URL(endpoint).openConnection() as HttpsURLConnection
                c.connectTimeout = 8000; c.readTimeout = 10000; c.requestMethod = "GET"; c.setRequestProperty("User-Agent", "WINSUNG98/4.1")
                val body = c.inputStream.bufferedReader().use { it.readText() }
                c.disconnect()
                val arr = JSONObject(body).optJSONArray("articles")
                val stories = ArrayList<Array<String>>()
                if (arr != null) for (i in 0 until minOf(arr.length(), 24)) {
                    val o = arr.optJSONObject(i) ?: continue
                    val t = o.optString("title").trim(); val u = o.optString("url").trim()
                    if (t.isNotBlank() && u.startsWith("https://")) stories.add(arrayOf(t, o.optString("domain", "News"), u))
                }
                ui.post {
                    loading = false
                    if (stories.isEmpty()) showMessage("Headlines are unavailable. Use a source below.") else {
                        news.removeAllViews()
                        stories.forEachIndexed { idx, s ->
                            val row = LinearLayout(activity).apply {
                                orientation = LinearLayout.VERTICAL; background = inset(); setPadding(activity.wdp(7), activity.wdp(6), activity.wdp(7), activity.wdp(6)); isClickable = true; setOnClickListener { openUrl(s[2]) }
                                addView(TextView(activity).apply { text = s[0]; classicText(10.5f, Color.BLACK, true); maxLines = 3 })
                                addView(TextView(activity).apply { text = s[1]; classicText(8.5f, Color.DKGRAY); setPadding(0, activity.wdp(3), 0, 0) })
                            }
                            news.addView(row, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { if (idx > 0) topMargin = activity.wdp(4) })
                        }
                        lastLoad = System.currentTimeMillis()
                    }
                }
            } catch (_: Exception) {
                ui.post { loading = false; showMessage("Headlines are unavailable. Tap Refresh or use Google News, Reuters or AP.") }
            }
        }
    }
}

class MediaBridge(private val context: Context) {
    data class State(val title: String = "Nothing playing", val artist: String = "", val playing: Boolean = false)
    private val manager = context.getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
    private fun controller(): MediaController? = try {
        manager.getActiveSessions(ComponentName(context, NotificationListenerService::class.java)).firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING }
            ?: manager.getActiveSessions(ComponentName(context, NotificationListenerService::class.java)).firstOrNull()
    } catch (_: Exception) { null }
    fun state(): State {
        val c = controller() ?: return State()
        val m = c.metadata
        return State(m?.getString(MediaMetadata.METADATA_KEY_TITLE) ?: m?.getString(MediaMetadata.METADATA_KEY_DISPLAY_TITLE) ?: "Media", m?.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: "", c.playbackState?.state == PlaybackState.STATE_PLAYING)
    }
    fun toggle() { controller()?.let { if (it.playbackState?.state == PlaybackState.STATE_PLAYING) it.transportControls.pause() else it.transportControls.play() } }
    fun next() { controller()?.transportControls?.skipToNext() }
    fun prev() { controller()?.transportControls?.skipToPrevious() }
}

class SecondaryPage(private val activity: MainActivity, onSwipe: (Int) -> Unit) : SwipePageFrame(activity, onSwipe) {
    private val ui = Handler(Looper.getMainLooper())
    private val media = MediaBridge(activity)
    private val clock = TextView(activity)
    private val date = TextView(activity)
    private val title = TextView(activity)
    private val artist = TextView(activity)
    private val play = TextView(activity)
    private val tick = object : Runnable { override fun run() { update(); ui.postDelayed(this, 1000L) } }

    init {
        setBackgroundColor(DESKTOP_TEAL)
        val root = FrameLayout(activity)
        addView(root, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        root.post {
            val top = root.rootWindowInsets?.systemWindowInsetTop ?: 0
            root.setPadding(activity.wdp(8), top + activity.wdp(8), activity.wdp(8), activity.wdp(8))
        }

        val iconRow = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.START }
        listOf(
            Triple("My Computer", "custom_icons_98/computer-0.webp", { activity.winsungOpenMyComputer() }),
            Triple("Pictures", "custom_icons_98/image_old_gif-0.webp", { activity.winsungOpenPictures() }),
            Triple("Notes", "custom_icons_programs/Notes.webp", { activity.winsungOpenNotepad() }),
            Triple("Programs", "custom_icons_98/appwizard_list.webp", { activity.winsungOpenGames() })
        ).forEach { (label, icon, action) -> iconRow.addView(desktopShortcut(label, icon, action), LinearLayout.LayoutParams(0, activity.wdp(78), 1f)) }
        root.addView(iconRow, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(82), Gravity.TOP))

        val dateWindow = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL; background = raised(); setPadding(activity.wdp(3), activity.wdp(3), activity.wdp(3), activity.wdp(3))
            addView(titleBar(activity, "Date & Time", "custom_icons_98/Clock.webp"), LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(24)))
            val body = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(activity.wdp(9), activity.wdp(8), activity.wdp(9), activity.wdp(8)) }
            body.addView(LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL; background = inset(); gravity = Gravity.CENTER; setPadding(activity.wdp(8), activity.wdp(5), activity.wdp(8), activity.wdp(5))
                addView(TextView(activity).apply { text = "DATE"; classicText(8f, Color.WHITE, true); gravity = Gravity.CENTER; background = GradientDrawable().apply { setColor(NAVY) } }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(18)))
                addView(date.apply { classicText(13f, Color.BLACK, true); gravity = Gravity.CENTER; setPadding(0, activity.wdp(5), 0, activity.wdp(5)) })
            }, LinearLayout.LayoutParams(0, activity.wdp(78), 1f))
            body.addView(LinearLayout(activity).apply {
                orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER; background = inset(); addView(ImageView(activity).apply { setImageDrawable(assetDrawable(activity, "custom_icons_98/Clock.webp")); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LinearLayout.LayoutParams(activity.wdp(48), activity.wdp(48))); addView(clock.apply { classicText(12f, Color.BLACK, false); gravity = Gravity.CENTER })
            }, LinearLayout.LayoutParams(0, activity.wdp(78), 1f).apply { marginStart = activity.wdp(8) })
            addView(body)
            addView(classicButton(activity, "Date/Time Properties") { activity.winsungOpenClock() }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(27)).apply { leftMargin = activity.wdp(8); rightMargin = activity.wdp(8); bottomMargin = activity.wdp(6) })
        }
        root.addView(dateWindow, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(145), Gravity.TOP).apply { topMargin = activity.wdp(92) })

        val mediaWindow = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL; background = raised(); setPadding(activity.wdp(3), activity.wdp(3), activity.wdp(3), activity.wdp(3))
            addView(titleBar(activity, "Media Player", "custom_icons_98/media_player-0.webp"), LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(24)))
            val menu = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; listOf("File", "Playback", "Options").forEach { m -> addView(TextView(activity).apply { text = m; classicText(9.5f); setPadding(activity.wdp(7), 0, activity.wdp(7), 0) }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, activity.wdp(24))) } }
            addView(menu)
            val display = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setBackgroundColor(Color.rgb(0, 37, 54)); setPadding(activity.wdp(8), activity.wdp(6), activity.wdp(8), activity.wdp(6)) }
            display.addView(ImageView(activity).apply { setImageDrawable(assetDrawable(activity, "custom_icons_98/media_player-0.webp")); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LinearLayout.LayoutParams(activity.wdp(42), activity.wdp(42)).apply { marginEnd = activity.wdp(10) })
            display.addView(LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL; addView(TextView(activity).apply { text = "MEDIA PLAYER"; classicText(8f, Color.rgb(121, 203, 212)); letterSpacing = .12f }); addView(title.apply { classicText(13f, Color.WHITE, true); maxLines = 1 }); addView(artist.apply { classicText(9f, Color.rgb(180, 203, 210)); maxLines = 1 }) }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            addView(display, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(65)).apply { leftMargin = activity.wdp(4); rightMargin = activity.wdp(4) })
            val controls = LinearLayout(activity).apply {
                orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; setPadding(activity.wdp(4), activity.wdp(4), activity.wdp(4), activity.wdp(4))
                addView(classicButton(activity, "|<") { media.prev(); update() }, LinearLayout.LayoutParams(0, activity.wdp(30), 1f))
                addView(play.apply { text = ">"; classicText(11f); gravity = Gravity.CENTER; background = raised(); isClickable = true; setOnClickListener { media.toggle(); ui.postDelayed({ update() }, 150) } }, LinearLayout.LayoutParams(0, activity.wdp(30), 1f).apply { marginStart = activity.wdp(4) })
                addView(classicButton(activity, ">|") { media.next(); update() }, LinearLayout.LayoutParams(0, activity.wdp(30), 1f).apply { marginStart = activity.wdp(4) })
                addView(classicButton(activity, "Open music") { activity.winsungOpenWmp() }, LinearLayout.LayoutParams(0, activity.wdp(30), 1.5f).apply { marginStart = activity.wdp(8) })
            }
            addView(controls)
        }
        root.addView(mediaWindow, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(180), Gravity.BOTTOM))
        update()
    }

    private fun desktopShortcut(label: String, icon: String, action: () -> Unit): LinearLayout = LinearLayout(activity).apply {
        orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL; isClickable = true; setOnClickListener { action() }
        addView(ImageView(activity).apply { setImageDrawable(assetDrawable(activity, icon)); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LinearLayout.LayoutParams(activity.wdp(42), activity.wdp(42)))
        addView(TextView(activity).apply { text = label; classicText(9.5f, Color.WHITE, false); gravity = Gravity.CENTER; setShadowLayer(2f, 1f, 1f, Color.BLACK); maxLines = 1 })
    }

    fun shown() { ui.removeCallbacks(tick); ui.post(tick) }
    fun hidden() { ui.removeCallbacks(tick) }
    private fun update() {
        val now = Date(); clock.text = SimpleDateFormat("h:mm:ss a", Locale.US).format(now); date.text = SimpleDateFormat("MMM d, yyyy", Locale.US).format(now)
        val s = media.state(); title.text = s.title; artist.text = s.artist.ifBlank { "No active media session" }; play.text = if (s.playing) "||" else ">"
    }
}

private class AolBackdrop(context: Context) : View(context) {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        p.shader = LinearGradient(0f, 0f, width.toFloat(), height.toFloat(), Color.rgb(38, 129, 194), Color.rgb(18, 93, 151), Shader.TileMode.CLAMP)
        c.drawRect(0f, 0f, width.toFloat(), height.toFloat(), p)
        p.shader = null; p.color = Color.argb(55, 190, 230, 255)
        val step = context.wdp(8).coerceAtLeast(5)
        var y = 0
        while (y < height) { var x = (y / step % 2) * step / 2; while (x < width) { c.drawCircle(x.toFloat(), y.toFloat(), 1.2f, p); x += step }; y += step }
    }
}

private class AolEyeView(context: Context, private val top: Int, private val mid: Int, private val bottom: Int) : View(context) {
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val path = Path()
    override fun onDraw(c: Canvas) {
        val w = width.toFloat(); val h = height.toFloat(); val cy = h / 2f
        path.reset(); path.moveTo(0f, cy); path.cubicTo(w * .17f, h * .05f, w * .35f, 0f, w * .5f, 0f); path.cubicTo(w * .65f, 0f, w * .83f, h * .05f, w, cy); path.cubicTo(w * .83f, h * .95f, w * .65f, h, w * .5f, h); path.cubicTo(w * .35f, h, w * .17f, h * .95f, 0f, cy); path.close()
        p.shader = LinearGradient(0f, 0f, 0f, h, intArrayOf(top, mid, bottom), floatArrayOf(0f, .46f, 1f), Shader.TileMode.CLAMP)
        c.drawPath(path, p); p.shader = null
        p.style = Paint.Style.STROKE; p.strokeWidth = context.wdp(1).toFloat(); p.color = Color.argb(190, 255, 255, 255); c.drawPath(path, p); p.style = Paint.Style.FILL
        p.color = Color.argb(90, 255, 255, 255); c.drawOval(w * .2f, h * .09f, w * .8f, h * .27f, p)
    }
}

private class AolChannelView(context: Context, label: String, iconPath: String, colors: IntArray, action: () -> Unit) : FrameLayout(context) {
    init {
        isClickable = true; setOnClickListener { action() }
        addView(AolEyeView(context, colors[0], colors[1], colors[2]), LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        addView(ImageView(context).apply { setImageDrawable(assetDrawable(context, iconPath)); scaleType = ImageView.ScaleType.CENTER_INSIDE }, LayoutParams(context.wdp(30), context.wdp(30), Gravity.CENTER_VERTICAL or Gravity.START).apply { leftMargin = context.wdp(28) })
        addView(TextView(context).apply { text = label; classicText(14f, Color.WHITE, true); gravity = Gravity.CENTER; setShadowLayer(3f, 2f, 2f, Color.rgb(20, 35, 90)); setPadding(context.wdp(48), 0, context.wdp(10), 0) }, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
    }
}

class AolPage(private val activity: MainActivity, onSwipe: (Int) -> Unit, private val channels: Boolean, private val quick: () -> Unit) : SwipePageFrame(activity, onSwipe) {
    init {
        val bg = AolBackdrop(activity)
        addView(bg, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        val root = FrameLayout(activity)
        addView(root, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        root.post { val top = root.rootWindowInsets?.systemWindowInsetTop ?: 0; root.setPadding(activity.wdp(12), top + activity.wdp(10), activity.wdp(12), activity.wdp(10)) }

        root.addView(TextView(activity).apply { text = if (channels) "AOL CHANNELS" else "AOL MAIN MENU"; classicText(11f, Color.WHITE, true); gravity = Gravity.CENTER; setPadding(activity.wdp(8), 0, activity.wdp(8), 0); background = ClassicBevelDrawable(NAVY, false) }, FrameLayout.LayoutParams(activity.wdp(125), activity.wdp(30), Gravity.TOP or Gravity.START))
        root.addView(LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_HORIZONTAL
            addView(TextView(activity).apply { text = "AOL"; classicText(43f, Color.rgb(160, 235, 255), true); typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD_ITALIC); setShadowLayer(4f, -2f, 3f, Color.rgb(4, 55, 120)) })
            addView(TextView(activity).apply { text = "AMERICA ONLINE"; classicText(8.5f, Color.WHITE, false); letterSpacing = .14f; gravity = Gravity.CENTER })
        }, FrameLayout.LayoutParams(activity.wdp(155), activity.wdp(78), Gravity.TOP or Gravity.END).apply { topMargin = activity.wdp(5) })

        val items = if (!channels) listOf(
            Triple("TODAY'S NEWS", "custom_icons_98/newspaper.webp", quick),
            Triple("WEATHER", "custom_icons_98/Weather.webp", { if (!activity.winsungLaunchByKeywords(arrayOf("weather"))) activity.winsungOpenInternet("https://www.weather.com/") }),
            Triple("INTERNET", "custom_icons/Internet Explorer 6.webp", { activity.winsungOpenInternet("https://www.google.com/") }),
            Triple("CHAT", "winsung_fixed/signal.png", { if (!activity.winsungLaunchPackage(arrayOf("org.thoughtcrime.securesms", "com.whatsapp"))) activity.winsungShowToast("Signal or WhatsApp is not installed") })
        ) else listOf(
            Triple("FINANCE", "custom_icons_98/world-0.webp", { activity.winsungOpenInternet("https://www.google.com/finance/") }),
            Triple("GAMES", "custom_icons_98/game_solitaire-0.webp", { activity.winsungOpenGames() }),
            Triple("COMPUTING", "custom_icons_98/computer-0.webp", { activity.winsungOpenMyComputer() }),
            Triple("TRAVEL", "custom_icons_98/world-1.webp", { activity.winsungOpenInternet("https://www.google.com/travel/") })
        )
        val colors = listOf(
            intArrayOf(Color.rgb(255, 246, 88), Color.rgb(42, 125, 240), Color.rgb(6, 31, 105)),
            intArrayOf(Color.rgb(255, 248, 116), Color.rgb(237, 62, 144), Color.rgb(141, 17, 96)),
            intArrayOf(Color.rgb(112, 255, 235), Color.rgb(19, 137, 185), Color.rgb(5, 70, 95)),
            intArrayOf(Color.rgb(255, 236, 69), Color.rgb(240, 108, 29), Color.rgb(142, 43, 0))
        )
        val holder = FrameLayout(activity)
        root.addView(holder, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT).apply { topMargin = activity.wdp(93); bottomMargin = activity.wdp(35) })
        items.forEachIndexed { i, x ->
            val v = AolChannelView(activity, x.first, x.second, colors[i], x.third)
            holder.addView(v, FrameLayout.LayoutParams(activity.wdp(175), activity.wdp(74)).apply {
                gravity = if (i % 2 == 0) Gravity.START else Gravity.END
                topMargin = activity.wdp(18 + i * 100)
                if (i % 2 == 0) leftMargin = activity.wdp(8) else rightMargin = activity.wdp(8)
            })
        }
        root.addView(TextView(activity).apply { text = "Click a channel to open the matching WINSUNG destination"; classicText(8.5f, Color.rgb(220, 242, 255)); gravity = Gravity.CENTER; setPadding(0, activity.wdp(4), 0, 0) }, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, activity.wdp(24), Gravity.BOTTOM))
    }
}

class Winsung98Controller(private val activity: MainActivity) {
    companion object { const val QUICK = 0; const val DESKTOP = 1; const val SECOND = 2; const val AOL1 = 3; const val AOL2 = 4; const val COUNT = 5 }
    private val bg = activity.findViewById<RelativeLayout>(R.id.main_background)
    private val overlay = FrameLayout(activity)
    private val dock = LinearLayout(activity)
    private val dots = LinearLayout(activity)
    private val topSystemChrome = View(activity).apply {
        setBackgroundColor(FACE)
        visibility = View.GONE
        elevation = activity.wdp(220).toFloat()
        isClickable = false
        isFocusable = false
    }
    private val badges = mutableMapOf<String, TextView>()
    private val ui = Handler(Looper.getMainLooper())
    private val originalStatusBarColor = activity.window.statusBarColor
    private val originalNavigationBarColor = activity.window.navigationBarColor
    private val originalSystemUiVisibility = activity.window.decorView.systemUiVisibility
    private var page = DESKTOP
    private var classic = false
    private val quick = QuickGlancePage(activity, ::swipe, activity::winsungOpenInternet, activity::winsungOpenCalendar) { show(SECOND) }
    private val second = SecondaryPage(activity, ::swipe)
    private val aol1 = AolPage(activity, ::swipe, false) { show(QUICK) }
    private val aol2 = AolPage(activity, ::swipe, true) { show(QUICK) }
    private val badgeTick = object : Runnable { override fun run() { if (classic) { refreshBadges(); ui.postDelayed(this, 1500L) } } }

    init {
        overlay.visibility = View.GONE
        val lp = RelativeLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT).apply { addRule(RelativeLayout.ALIGN_PARENT_TOP); bottomMargin = activity.wdp(66) }
        val fw = bg.findViewById<View>(R.id.floating_windows_container)
        bg.addView(overlay, bg.indexOfChild(fw).coerceAtLeast(1), lp)
        listOf(quick, second, aol1, aol2).forEach { overlay.addView(it, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)); it.visibility = View.GONE }

        bg.addView(
            topSystemChrome,
            RelativeLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                1
            ).apply { addRule(RelativeLayout.ALIGN_PARENT_TOP) }
        )
        topSystemChrome.post {
            val inset = topSystemChrome.rootWindowInsets?.systemWindowInsetTop ?: 0
            val p = topSystemChrome.layoutParams
            p.height = inset.coerceAtLeast(1)
            topSystemChrome.layoutParams = p
        }

        buildDots(); buildDock(); updateDots()
    }

    fun theme(t: AppTheme) {
        classic = t is AppTheme.WindowsClassic
        dots.visibility = if (classic) View.VISIBLE else View.GONE

        if (!classic) {
            ui.removeCallbacks(badgeTick)
            dock.visibility = View.GONE
            quick.hidden()
            second.hidden()
            page = DESKTOP
            overlay.visibility = View.GONE

            activity.window.statusBarColor = originalStatusBarColor
            activity.window.navigationBarColor = originalNavigationBarColor
            activity.window.decorView.systemUiVisibility = originalSystemUiVisibility
            activity.findViewById<View>(R.id.root_container)?.setBackgroundColor(Color.BLACK)
            activity.findViewById<View>(R.id.gesture_bar_background)?.setBackgroundColor(Color.BLACK)
            activity.findViewById<View>(R.id.system_tray)?.visibility = View.VISIBLE
            topSystemChrome.visibility = View.GONE
        } else {
            // Windows 98 owns the full visual edge.  The Android status/navigation
            // areas use the same classic face colour so there is no black strip above
            // or below the desktop/taskbar.
            activity.window.statusBarColor = FACE
            activity.window.navigationBarColor = FACE
            var flags = originalSystemUiVisibility or View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                flags = flags or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
            }
            activity.window.decorView.systemUiVisibility = flags
            activity.findViewById<View>(R.id.root_container)?.setBackgroundColor(FACE)
            activity.findViewById<View>(R.id.gesture_bar_background)?.setBackgroundColor(FACE)
            topSystemChrome.visibility = View.VISIBLE
            topSystemChrome.post {
                val inset = topSystemChrome.rootWindowInsets?.systemWindowInsetTop ?: 0
                val p = topSystemChrome.layoutParams
                p.height = inset.coerceAtLeast(1)
                topSystemChrome.layoutParams = p
                topSystemChrome.bringToFront()
            }

            attachDockToTaskbar()
            dock.visibility = View.VISIBLE
            ui.removeCallbacks(badgeTick)
            ui.post(badgeTick)
            show(DESKTOP, false)
        }
    }

    fun swipe(dir: Int) { if (classic) show((page + dir).coerceIn(0, COUNT - 1)) }
    fun quick() { show(QUICK) }
    fun show(target: Int, animate: Boolean = true) {
        if (!classic) return
        val old = page; page = target.coerceIn(0, COUNT - 1); quick.hidden(); second.hidden(); listOf(quick, second, aol1, aol2).forEach { it.visibility = View.GONE }
        if (page == DESKTOP) overlay.visibility = View.GONE else {
            val v = when (page) { QUICK -> quick; SECOND -> second; AOL1 -> aol1; else -> aol2 }
            v.visibility = View.VISIBLE; overlay.visibility = View.VISIBLE
            if (animate) { val w = bg.width.takeIf { it > 0 } ?: activity.resources.displayMetrics.widthPixels; overlay.translationX = if (page > old) w.toFloat() else -w.toFloat(); overlay.animate().translationX(0f).setDuration(170).setInterpolator(DecelerateInterpolator()).start() }
            if (page == QUICK) quick.shown(); if (page == SECOND) second.shown()
        }
        updateDots(); refreshBadges()
    }

    fun refreshBadges() {
        if (!classic) return
        FIXED_APPS.forEach { a ->
            val n = a.packages.sumOf { NotificationListenerService.getNotificationCount(it) }
            badges[a.label]?.let { b -> b.text = if (n > 99) "99+" else "$n"; b.visibility = if (n > 0) View.VISIBLE else View.GONE }
        }
    }

    private fun buildDots() {
        dots.orientation = LinearLayout.HORIZONTAL; dots.gravity = Gravity.CENTER
        val lp = RelativeLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, activity.wdp(18)).apply { addRule(RelativeLayout.ALIGN_PARENT_BOTTOM); addRule(RelativeLayout.CENTER_HORIZONTAL); bottomMargin = activity.wdp(40) }
        bg.addView(dots, lp)
        repeat(COUNT) { dots.addView(View(activity), LinearLayout.LayoutParams(activity.wdp(7), activity.wdp(7)).apply { marginStart = activity.wdp(4); marginEnd = activity.wdp(4) }) }
    }

    private fun updateDots() {
        for (i in 0 until dots.childCount) dots.getChildAt(i).background = GradientDrawable().apply { shape = GradientDrawable.RECTANGLE; setColor(if (i == page) Color.WHITE else Color.TRANSPARENT); setStroke(1, if (i == page) Color.WHITE else Color.rgb(125, 210, 210)) }
    }

    private fun buildDock() {
        dock.orientation = LinearLayout.HORIZONTAL; dock.gravity = Gravity.CENTER_VERTICAL; dock.background = null
        FIXED_APPS.forEachIndexed { i, a ->
            val f = FrameLayout(activity).apply { background = raised(); isClickable = true; contentDescription = a.label; setOnClickListener { if (!activity.winsungLaunchPackage(a.packages.toTypedArray())) activity.winsungShowToast("${a.label} is not installed") } }
            val icon = ImageView(activity).apply { scaleType = ImageView.ScaleType.CENTER_INSIDE; setImageDrawable(assetDrawable(activity, a.asset) ?: assetDrawable(activity, when (a.label) { "Phone" -> "custom_icons_98/Phone.webp"; "Signal" -> "custom_icons_98/Mail.webp"; "Firefox" -> "custom_icons/Internet Explorer 6.webp"; "WhatsApp" -> "custom_icons_98/WhatsApp.webp"; else -> "custom_icons_98/media_player-0.webp" })) }
            f.addView(icon, FrameLayout.LayoutParams(activity.wdp(25), activity.wdp(25), Gravity.CENTER))
            val b = TextView(activity).apply { visibility = View.GONE; classicText(7.5f, Color.WHITE, true); gravity = Gravity.CENTER; minWidth = activity.wdp(15); background = GradientDrawable().apply { shape = GradientDrawable.OVAL; setColor(Color.rgb(190, 0, 0)); setStroke(1, Color.WHITE) } }
            badges[a.label] = b
            f.addView(b, FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, activity.wdp(16), Gravity.TOP or Gravity.END).apply { topMargin = -activity.wdp(1); rightMargin = -activity.wdp(1) })
            dock.addView(f, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f).apply { if (i > 0) marginStart = activity.wdp(2) })
        }
    }

    private fun attachDockToTaskbar() {
        val host = activity.findViewById<LinearLayout>(R.id.taskbar_empty_space) ?: return
        (dock.parent as? ViewGroup)?.removeView(dock)

        // WINSUNG Win98 taskbar: Start + exactly five fixed applications.
        // Remove the inherited AQI/weather/volume/date/clock tray completely.
        activity.findViewById<View>(R.id.system_tray)?.visibility = View.GONE
        (host.layoutParams as? RelativeLayout.LayoutParams)?.let { lp ->
            lp.removeRule(RelativeLayout.LEFT_OF)
            lp.addRule(RelativeLayout.ALIGN_PARENT_RIGHT)
            host.layoutParams = lp
        }
        host.setPadding(activity.wdp(4), 0, activity.wdp(4), 0)
        host.removeAllViews()
        host.addView(
            dock,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )
    }
}
