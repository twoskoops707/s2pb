package com.s2pb.skillsindex;

import android.app.Activity;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.HorizontalScrollView;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.ScrollView;
import android.widget.TextView;

public class SettingsActivity extends Activity {

    static final String PREFS = "theme";
    static final String KEY_BG = "bg";
    static final String KEY_FG = "fg";
    static final String KEY_FONT = "font_idx";

    private static final String[] COLOR_NAMES = {
        "Off-white", "White", "Cream", "Light Gray",
        "Ink", "Charcoal", "Navy", "Slate", "Deep Green", "Deep Plum"
    };
    private static final String[] COLOR_HEX = {
        "#F4F4F2", "#FFFFFF", "#F6F1E8", "#E8E8E6",
        "#17181C", "#1B1C1F", "#0F1B2B", "#33363D", "#10241A", "#201229"
    };

    static final String[] FONT_NAMES = {"System", "Serif", "Monospace"};
    static final String[] FONT_CSS = {
        "-apple-system, BlinkMacSystemFont, \"Segoe UI\", system-ui, sans-serif",
        "Georgia, \"Times New Roman\", serif",
        "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    };

    private static final int ACCENT = Color.parseColor("#2B4F7E");
    private static final int UNSELECTED_BORDER = Color.parseColor("#DADADA");

    private String selectedBg;
    private String selectedFg;
    private int selectedFontIdx;

    private LinearLayout bgRow;
    private LinearLayout fgRow;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        selectedBg = prefs.getString(KEY_BG, COLOR_HEX[0]);
        selectedFg = prefs.getString(KEY_FG, COLOR_HEX[4]);
        selectedFontIdx = prefs.getInt(KEY_FONT, 0);

        int pad = dp(20);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad, pad, pad);
        root.setBackgroundColor(Color.WHITE);

        root.addView(sectionLabel("Background color"));
        bgRow = new LinearLayout(this);
        bgRow.setOrientation(LinearLayout.HORIZONTAL);
        wrapRow(bgRow);
        root.addView(scrollableRow(bgRow));

        root.addView(spacer());
        root.addView(sectionLabel("Text color"));
        fgRow = new LinearLayout(this);
        fgRow.setOrientation(LinearLayout.HORIZONTAL);
        wrapRow(fgRow);
        root.addView(scrollableRow(fgRow));

        buildSwatches(bgRow, true);
        buildSwatches(fgRow, false);

        root.addView(spacer());
        root.addView(sectionLabel("Font"));
        RadioGroup fontGroup = new RadioGroup(this);
        fontGroup.setOrientation(RadioGroup.VERTICAL);
        for (int i = 0; i < FONT_NAMES.length; i++) {
            RadioButton rb = new RadioButton(this);
            rb.setText(FONT_NAMES[i]);
            rb.setId(View.generateViewId());
            rb.setChecked(i == selectedFontIdx);
            final int idx = i;
            rb.setOnClickListener(v -> selectedFontIdx = idx);
            fontGroup.addView(rb);
        }
        root.addView(fontGroup);

        root.addView(spacer());
        Button apply = new Button(this);
        apply.setText("Apply");
        apply.setOnClickListener(v -> {
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString(KEY_BG, selectedBg)
                .putString(KEY_FG, selectedFg)
                .putInt(KEY_FONT, selectedFontIdx)
                .apply();
            setResult(RESULT_OK);
            finish();
        });
        root.addView(apply);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);
    }

    private void buildSwatches(LinearLayout row, boolean isBg) {
        row.removeAllViews();
        for (int i = 0; i < COLOR_HEX.length; i++) {
            row.addView(makeSwatch(COLOR_HEX[i], isBg));
        }
    }

    private View makeSwatch(String hex, boolean isBg) {
        View v = new View(this);
        int size = dp(36);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(size, size);
        int m = dp(4);
        lp.setMargins(m, m, m, m);
        v.setLayoutParams(lp);

        boolean selected = hex.equalsIgnoreCase(isBg ? selectedBg : selectedFg);
        GradientDrawable gd = new GradientDrawable();
        gd.setColor(Color.parseColor(hex));
        gd.setCornerRadius(dp(4));
        gd.setStroke(selected ? dp(3) : dp(1), selected ? ACCENT : UNSELECTED_BORDER);
        v.setBackground(gd);

        v.setOnClickListener(view -> {
            if (isBg) {
                selectedBg = hex;
                buildSwatches(bgRow, true);
            } else {
                selectedFg = hex;
                buildSwatches(fgRow, false);
            }
        });
        return v;
    }

    private TextView sectionLabel(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(13);
        tv.setTextColor(Color.parseColor("#7A7A75"));
        return tv;
    }

    private View spacer() {
        View v = new View(this);
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(20)));
        return v;
    }

    private void wrapRow(LinearLayout row) {
        row.setGravity(Gravity.START);
        row.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
    }

    private View scrollableRow(LinearLayout row) {
        // 10 swatches at ~44dp each can exceed a narrow phone's width;
        // a horizontal scroller keeps them all reachable with no extra deps.
        HorizontalScrollView hsv = new HorizontalScrollView(this);
        hsv.setLayoutParams(new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        hsv.addView(row);
        return hsv;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
