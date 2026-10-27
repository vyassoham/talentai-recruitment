package ai.talentai.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.DownloadManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class UpdateManager {
    private static final String TAG = "TalentAI-UpdateManager";
    private static final String VERSION_CHECK_URL = "https://talentai-recruitment.onrender.com/api/v1/app/version";

    private final Activity activity;
    private final Handler mainHandler;
    private final ExecutorService executor;

    public UpdateManager(Activity activity) {
        this.activity = activity;
        this.mainHandler = new Handler(Looper.getMainLooper());
        this.executor = Executors.newSingleThreadExecutor();
    }

    public void checkForUpdates(final boolean manualCheck) {
        executor.execute(() -> {
            try {
                URL url = new URL(VERSION_CHECK_URL);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);
                conn.setRequestProperty("Accept", "application/json");

                int responseCode = conn.getResponseCode();
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder response = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    reader.close();

                    JSONObject json = new JSONObject(response.toString());
                    int latestVersionCode = json.optInt("latest_version_code", 0);
                    String latestVersionName = json.optString("latest_version", "1.0.0");
                    String downloadUrl = json.optString("download_url", "");
                    String releaseNotes = json.optString("release_notes", "Performance improvements and bug fixes.");
                    boolean mandatory = json.optBoolean("mandatory", false);

                    int currentVersionCode = BuildConfig.VERSION_CODE;

                    if (latestVersionCode > currentVersionCode) {
                        mainHandler.post(() -> showUpdateDialog(latestVersionName, downloadUrl, releaseNotes, mandatory));
                    } else if (manualCheck) {
                        mainHandler.post(() -> Toast.makeText(activity, "TalentAI is up to date (v" + BuildConfig.VERSION_NAME + ")", Toast.LENGTH_SHORT).show());
                    }
                } else if (manualCheck) {
                    mainHandler.post(() -> Toast.makeText(activity, "Unable to check updates: HTTP " + responseCode, Toast.LENGTH_SHORT).show());
                }
            } catch (Exception e) {
                Log.e(TAG, "Update check failed", e);
                if (manualCheck) {
                    mainHandler.post(() -> Toast.makeText(activity, "Update check failed: " + e.getMessage(), Toast.LENGTH_SHORT).show());
                }
            }
        });
    }

    private void showUpdateDialog(String versionName, String downloadUrl, String notes, boolean mandatory) {
        if (activity.isFinishing()) return;

        AlertDialog.Builder builder = new AlertDialog.Builder(activity)
                .setTitle("Update Available: v" + versionName)
                .setMessage(notes)
                .setCancelable(!mandatory)
                .setPositiveButton("Update Now", (dialog, which) -> {
                    startDownloadAndInstall(downloadUrl, versionName);
                });

        if (!mandatory) {
            builder.setNegativeButton("Later", (dialog, which) -> dialog.dismiss());
        }

        builder.show();
    }

    private void startDownloadAndInstall(String downloadUrl, String versionName) {
        Toast.makeText(activity, "Downloading TalentAI v" + versionName + "...", Toast.LENGTH_LONG).show();

        try {
            File destination = new File(activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "TalentAI-v" + versionName + ".apk");
            if (destination.exists()) {
                destination.delete();
            }

            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(downloadUrl));
            request.setTitle("TalentAI Enterprise Update");
            request.setDescription("Downloading version " + versionName);
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationUri(Uri.fromFile(destination));
            request.setMimeType("application/vnd.android.package-archive");

            DownloadManager downloadManager = (DownloadManager) activity.getSystemService(Context.DOWNLOAD_SERVICE);
            if (downloadManager == null) {
                Toast.makeText(activity, "DownloadManager unavailable", Toast.LENGTH_SHORT).show();
                return;
            }

            final long downloadId = downloadManager.enqueue(request);

            BroadcastReceiver receiver = new BroadcastReceiver() {
                @Override
                public void onReceive(Context context, Intent intent) {
                    long id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1);
                    if (id == downloadId) {
                        activity.unregisterReceiver(this);
                        installApk(destination);
                    }
                }
            };

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                activity.registerReceiver(receiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE), Context.RECEIVER_EXPORTED);
            } else {
                activity.registerReceiver(receiver, new IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE));
            }

        } catch (Exception e) {
            Log.e(TAG, "Failed to start download", e);
            // Fallback to opening download URL directly in browser
            try {
                Intent browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(downloadUrl));
                activity.startActivity(browserIntent);
            } catch (Exception ex) {
                Toast.makeText(activity, "Download failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void installApk(File apkFile) {
        if (!apkFile.exists()) {
            Toast.makeText(activity, "Downloaded APK not found", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            Intent intent = new Intent(Intent.ACTION_VIEW);
            Uri apkUri = FileProvider.getUriForFile(
                    activity,
                    activity.getPackageName() + ".fileprovider",
                    apkFile
            );

            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);

            activity.startActivity(intent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to launch package installer", e);
            Toast.makeText(activity, "Failed to launch installer: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }
}
