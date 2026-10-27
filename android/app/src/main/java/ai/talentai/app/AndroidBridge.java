package ai.talentai.app;

import android.app.Activity;
import android.content.Intent;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

public class AndroidBridge {
    private final Activity activity;
    private final UpdateManager updateManager;

    public AndroidBridge(Activity activity, UpdateManager updateManager) {
        this.activity = activity;
        this.updateManager = updateManager;
    }

    @JavascriptInterface
    public String getAppVersion() {
        return BuildConfig.VERSION_NAME;
    }

    @JavascriptInterface
    public int getAppVersionCode() {
        return BuildConfig.VERSION_CODE;
    }

    @JavascriptInterface
    public void checkForUpdates() {
        if (updateManager != null) {
            updateManager.checkForUpdates(true);
        }
    }

    @JavascriptInterface
    public void shareCandidate(String name, String summary, String shareUrl) {
        Intent shareIntent = new Intent(Intent.ACTION_SEND);
        shareIntent.setType("text/plain");
        shareIntent.putExtra(Intent.EXTRA_SUBJECT, "Candidate Profile: " + name);
        String text = "TalentAI Candidate Profile:\n" + name + "\n" + summary + "\n" + (shareUrl != null ? shareUrl : "");
        shareIntent.putExtra(Intent.EXTRA_TEXT, text);
        activity.startActivity(Intent.createChooser(shareIntent, "Share Candidate Profile"));
    }

    @JavascriptInterface
    public void toast(String message) {
        activity.runOnUiThread(() -> Toast.makeText(activity, message, Toast.LENGTH_SHORT).show());
    }
}
