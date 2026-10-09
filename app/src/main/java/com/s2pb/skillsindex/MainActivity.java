package com.s2pb.skillsindex;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Full-screen WebView around assets/index.html. Catalog sources, best first:
 *   1. live helper on this phone (tools/s2pb_server.py, started by a Claude Code hook)
 *   2. a sync file the user picked once (persistable SAF grant)
 *   3. the snapshot bundled in the APK (assets/catalog.json)
 * Also checks GitHub Releases for a newer APK on launch.
 */
public class MainActivity extends Activity {

    private static final String API = "http://127.0.0.1:8765";
    private static final String RELEASES =
        "https://api.github.com/repos/twoskoops707/s2pb/releases/latest";
    private static final String SYNC_PREFS = "sync";
    private static final String KEY_CATALOG_URI = "catalog_uri";
    private static final int REQUEST_SYNC = 200;

    private WebView webView;
    private boolean pageLoaded = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow();
        w.setStatusBarColor(Color.parseColor("#0b0c0f"));
        w.setNavigationBarColor(Color.parseColor("#0b0c0f"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#0b0c0f"));
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.addJavascriptInterface(new Bridge(), "Android");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                if (pageLoaded) return;
                pageLoaded = true;
                loadCatalog();
                checkUpdate(false);
            }
        });
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (pageLoaded) loadCatalog();
    }

    @Override
    public void onBackPressed() {
        webView.evaluateJavascript("window.onBack && window.onBack()", handled -> {
            if (!"true".equals(handled)) superBack();
        });
    }

    private void superBack() {
        super.onBackPressed();
    }

    // ---------- catalog ----------

    private void loadCatalog() {
        new Thread(() -> {
            String json = httpGet(API + "/catalog", 1500);
            String source = "live";
            if (json == null) {
                json = readSavedUri();
                source = "file";
            }
            if (json == null) {
                json = readAsset("catalog.json");
                source = "bundled";
            }
            if (json != null) push(json, source);
        }).start();
    }

    private void push(String json, String source) {
        runOnUiThread(() -> webView.evaluateJavascript(
            "applyCatalog(" + JSONObject.quote(json) + "," + JSONObject.quote(source) + ");", null));
    }

    private void js(String code) {
        runOnUiThread(() -> webView.evaluateJavascript(code, null));
    }

    private void refreshLive() {
        new Thread(() -> {
            js("setRefreshing(true)");
            if (httpPost(API + "/refresh") == null) {
                js("setRefreshing(false, 'Helper not running — open Claude Code in Termux')");
                loadCatalog();
                return;
            }
            // full MCP health check takes 1-2 min; poll until done (max ~4 min)
            for (int i = 0; i < 120; i++) {
                sleep(2000);
                String st = httpGet(API + "/status", 1500);
                if (st == null) break;
                try {
                    if (!new JSONObject(st).optBoolean("running")) break;
                } catch (Exception ignored) {
                    break;
                }
            }
            loadCatalog();
            js("setRefreshing(false, 'Status refreshed')");
        }).start();
    }

    private String readSavedUri() {
        String saved = getSharedPreferences(SYNC_PREFS, MODE_PRIVATE).getString(KEY_CATALOG_URI, null);
        if (saved == null) return null;
        try (InputStream is = getContentResolver().openInputStream(Uri.parse(saved))) {
            return is == null ? null : readAll(is);
        } catch (Exception e) {
            return null;
        }
    }

    private String readAsset(String name) {
        try (InputStream is = getAssets().open(name)) {
            return readAll(is);
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_SYNC || resultCode != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        if (uri == null) return;
        try {
            getContentResolver().takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException ignored) {
            // some providers don't support persistable grants; this session's read still works
        }
        getSharedPreferences(SYNC_PREFS, MODE_PRIVATE).edit()
            .putString(KEY_CATALOG_URI, uri.toString()).apply();
        new Thread(() -> {
            String json = readSavedUri();
            if (json != null) push(json, "file");
            else js("setRefreshing(false, 'Sync failed: file not readable')");
        }).start();
    }

    // ---------- self-update ----------

    private void checkUpdate(boolean manual) {
        new Thread(() -> {
            String json = httpGet(RELEASES, 8000);
            try {
                JSONObject rel = new JSONObject(json);
                int latest = Integer.parseInt(rel.getString("tag_name").replaceAll("\\D", ""));
                String apkUrl = null;
                JSONArray assets = rel.getJSONArray("assets");
                for (int i = 0; i < assets.length(); i++) {
                    JSONObject a = assets.getJSONObject(i);
                    if (a.getString("name").endsWith(".apk")) apkUrl = a.getString("browser_download_url");
                }
                if (latest > versionCode() && apkUrl != null) {
                    js("showUpdate(" + JSONObject.quote(rel.getString("tag_name")) + ","
                        + JSONObject.quote(apkUrl) + ")");
                } else if (manual) {
                    js("setRefreshing(false, 'You have the latest version')");
                }
            } catch (Exception e) {
                if (manual) js("setRefreshing(false, 'Couldn\\'t check for updates')");
            }
        }).start();
    }

    @SuppressWarnings("deprecation")
    private int versionCode() {
        try {
            PackageInfo pi = getPackageManager().getPackageInfo(getPackageName(), 0);
            return Build.VERSION.SDK_INT >= 28 ? (int) pi.getLongVersionCode() : pi.versionCode;
        } catch (Exception e) {
            return 0;
        }
    }

    // ---------- JS bridge ----------

    private class Bridge {
        @JavascriptInterface
        public void refresh() {
            refreshLive();
        }

        @JavascriptInterface
        public void pickCatalogFile() {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            intent.setType("*/*");
            runOnUiThread(() -> startActivityForResult(intent, REQUEST_SYNC));
        }

        @JavascriptInterface
        public void copy(String text) {
            ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            runOnUiThread(() -> cm.setPrimaryClip(ClipData.newPlainText("Skills Index", text)));
        }

        @JavascriptInterface
        public void openUrl(String url) {
            if (!url.startsWith("https://")) return;
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        }

        @JavascriptInterface
        public void checkUpdate(boolean manual) {
            MainActivity.this.checkUpdate(manual);
        }

        @JavascriptInterface
        public String versionName() {
            try {
                return getPackageManager().getPackageInfo(getPackageName(), 0).versionName;
            } catch (Exception e) {
                return "?";
            }
        }
    }

    // ---------- io ----------

    private static String httpGet(String url, int timeoutMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(timeoutMs);
            c.setReadTimeout(timeoutMs * 10);
            c.setRequestProperty("Accept", "application/json");
            if (c.getResponseCode() != 200) return null;
            try (InputStream is = c.getInputStream()) {
                return readAll(is);
            }
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String httpPost(String url) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(url).openConnection();
            c.setConnectTimeout(1500);
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            try (OutputStream os = c.getOutputStream()) {
                os.write(new byte[0]);
            }
            int code = c.getResponseCode();
            return code >= 200 && code < 300 ? "ok" : null;
        } catch (Exception e) {
            return null;
        } finally {
            if (c != null) c.disconnect();
        }
    }

    private static String readAll(InputStream is) throws Exception {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[16384];
        int n;
        while ((n = is.read(chunk)) != -1) buffer.write(chunk, 0, n);
        return buffer.toString("UTF-8");
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ignored) {
        }
    }
}
