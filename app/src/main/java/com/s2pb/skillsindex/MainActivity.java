package com.s2pb.skillsindex;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

public class MainActivity extends Activity {

    private static final String SYNC_PREFS = "sync";
    private static final String KEY_CATALOG_URI = "catalog_uri";
    private static final int REQUEST_SETTINGS = 100;
    private static final int REQUEST_SYNC = 200;

    private WebView webView;
    private boolean pageLoaded = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);

        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setBackgroundColor(Color.parseColor("#2B4F7E"));
        int padH = dp(16);
        int padV = dp(10);
        topBar.setPadding(padH, padV, padH, padV);

        TextView title = new TextView(this);
        title.setText("Skills Index");
        title.setTextColor(Color.WHITE);
        title.setTextSize(16);
        LinearLayout.LayoutParams titleLp = new LinearLayout.LayoutParams(
            0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        title.setLayoutParams(titleLp);
        topBar.addView(title);

        Button syncBtn = flatButton("Sync");
        syncBtn.setOnClickListener(v -> launchSyncPicker());
        topBar.addView(syncBtn);

        Button settingsBtn = flatButton("Settings");
        settingsBtn.setOnClickListener(v ->
            startActivityForResult(new Intent(this, SettingsActivity.class), REQUEST_SETTINGS));
        topBar.addView(settingsBtn);

        root.addView(topBar);

        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                pageLoaded = true;
                applyThemeToWebView();
                resyncFromSavedUriIfAny(true);
            }
        });
        webView.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        webView.loadUrl("file:///android_asset/index.html");
        root.addView(webView);

        setContentView(root);
    }

    private Button flatButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(Color.WHITE);
        b.setTextSize(12);
        b.setBackgroundColor(Color.TRANSPARENT);
        b.setAllCaps(false);
        b.setMinWidth(0);
        b.setMinimumWidth(0);
        b.setPadding(dp(8), 0, dp(8), 0);
        return b;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_SETTINGS && resultCode == RESULT_OK) {
            applyThemeToWebView();
            return;
        }

        if (requestCode == REQUEST_SYNC && resultCode == RESULT_OK && data != null) {
            Uri uri = data.getData();
            if (uri == null) return;
            try {
                getContentResolver().takePersistableUriPermission(
                    uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
            } catch (SecurityException ignored) {
                // some providers don't support persistable grants; the read
                // below still works for this session even if it fails.
            }
            getSharedPreferences(SYNC_PREFS, MODE_PRIVATE).edit()
                .putString(KEY_CATALOG_URI, uri.toString())
                .apply();
            loadCatalogFromUri(uri, false);
        }
    }

    private void launchSyncPicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");
        startActivityForResult(intent, REQUEST_SYNC);
    }

    private void resyncFromSavedUriIfAny(boolean silent) {
        String saved = getSharedPreferences(SYNC_PREFS, MODE_PRIVATE)
            .getString(KEY_CATALOG_URI, null);
        if (saved == null) return;
        loadCatalogFromUri(Uri.parse(saved), silent);
    }

    private void loadCatalogFromUri(Uri uri, boolean silent) {
        new Thread(() -> {
            try (InputStream is = getContentResolver().openInputStream(uri)) {
                if (is == null) throw new IllegalStateException("no stream");
                String json = readAll(is);
                JSONArray arr = new JSONArray(json); // validates + gives a count
                int count = arr.length();
                runOnUiThread(() -> {
                    webView.evaluateJavascript(
                        "applyCatalog(" + JSONObject.quote(json) + ");", null);
                    if (!silent) {
                        Toast.makeText(this, "Synced " + count + " entries", Toast.LENGTH_SHORT).show();
                    }
                });
            } catch (Exception e) {
                if (!silent) {
                    runOnUiThread(() ->
                        Toast.makeText(this, "Sync failed: file not readable", Toast.LENGTH_SHORT).show());
                }
            }
        }).start();
    }

    private String readAll(InputStream is) throws Exception {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[8192];
        int n;
        while ((n = is.read(chunk)) != -1) {
            buffer.write(chunk, 0, n);
        }
        return buffer.toString("UTF-8");
    }

    private void applyThemeToWebView() {
        if (!pageLoaded) return;
        SharedPreferences prefs = getSharedPreferences(SettingsActivity.PREFS, MODE_PRIVATE);
        String bg = prefs.getString(SettingsActivity.KEY_BG, "#F4F4F2");
        String fg = prefs.getString(SettingsActivity.KEY_FG, "#17181C");
        int fontIdx = prefs.getInt(SettingsActivity.KEY_FONT, 0);
        String fontCss = SettingsActivity.FONT_CSS[
            Math.max(0, Math.min(fontIdx, SettingsActivity.FONT_CSS.length - 1))];

        String js = "applyTheme(" + JSONObject.quote(bg) + "," + JSONObject.quote(fg)
            + "," + JSONObject.quote(fontCss) + ");";
        webView.evaluateJavascript(js, null);
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
