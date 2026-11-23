/**
 * Eisenhower Matrix: backup to your own Google Drive
 *
 * A Google Apps Script that runs in YOUR Google account and saves the app's
 * backups into a folder in YOUR Google Drive. Nothing passes through the
 * app's developer. Setup steps:
 *   https://willtoforge.com/eisenhower-matrix/backup/connect/
 *
 * 1. Change SECRET below to a long random word only you know
 *    (letters, numbers, - or _ only, at least 20 characters).
 * 2. Deploy > New deployment > Web app. Execute as: Me. Who has access: Anyone.
 * 3. In the app (Settings > Backup & Sync > API Endpoint) enter:
 *      <your Web app URL>/<your SECRET>
 *    for example https://script.google.com/macros/s/AKfy.../exec/my-long-secret-word
 *    and leave API Key EMPTY (Google rejects the key header on script addresses).
 */

const SECRET = 'CHANGE-ME-to-a-long-random-word';
const FOLDER_NAME = 'Eisenhower Matrix backups';
const KEEP_PER_DEVICE = 30; // older backups of the same phone are moved to the Drive bin

function doGet(e) {
  return handle_(e, 'GET');
}

function doPost(e) {
  return handle_(e, 'POST');
}

function handle_(e, method) {
  try {
    if (SECRET.indexOf('CHANGE-ME') === 0 || SECRET.length < 20) {
      return json_({ error: 'Set SECRET in the script to your own long random word, then deploy again.' });
    }
    const parts = String((e && e.pathInfo) || '').split('/').filter(String);
    // Expected: <SECRET>/api/backup[/<deviceId>[/history]]
    if (parts[0] !== SECRET || parts[1] !== 'api' || parts[2] !== 'backup') {
      return json_({ error: 'Not found. Check the address in the app ends with /exec/<your SECRET>.' });
    }
    const rest = parts.slice(3);

    if (method === 'POST' && rest.length === 0) {
      const body = JSON.parse(e.postData.contents);
      const deviceId = safeId_(body.deviceId);
      if (!deviceId || !Array.isArray(body.tasks)) {
        return json_({ error: 'Not a backup.' });
      }
      const timestamp = String(body.timestamp || new Date().toISOString());
      const folder = folder_();
      folder.createFile(fileName_(deviceId, timestamp), JSON.stringify(body), 'application/json');
      prune_(folder, deviceId);
      return json_(meta_(deviceId, timestamp, body.tasks.length));
    }

    if (method === 'GET' && rest.length === 2 && rest[1] === 'history') {
      const deviceId = safeId_(rest[0]);
      return json_(files_(folder_(), deviceId).map(function (f) {
        return meta_(deviceId, timestampOf_(f.getName(), deviceId), null);
      }));
    }

    if (method === 'GET' && rest.length === 1) {
      const deviceId = safeId_(rest[0]);
      const files = files_(folder_(), deviceId);
      if (!files.length) {
        // Web apps always answer 200, so say it in the body. This is not a backup,
        // so the app refuses to restore it and your tasks stay as they are.
        return json_({ error: 'No backup for this device ID yet.' });
      }
      return ContentService.createTextOutput(files[0].getBlob().getDataAsString())
        .setMimeType(ContentService.MimeType.JSON);
    }

    return json_({ error: 'Not supported.' });
  } catch (err) {
    return json_({ error: String(err && err.message || err) });
  }
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function safeId_(id) {
  return String(id || '').replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 100);
}

function fileName_(deviceId, timestamp) {
  return deviceId + '__' + timestamp.replace(/:/g, '-') + '.json';
}

function timestampOf_(name, deviceId) {
  // 2026-11-23T20-15-00.000Z -> 2026-11-23T20:15:00.000Z
  const stamp = name.slice(deviceId.length + 2, -5);
  return stamp.replace(/T(\d\d)-(\d\d)-(\d\d)/, 'T$1:$2:$3');
}

function meta_(deviceId, timestamp, taskCount) {
  const m = { id: deviceId + '__' + timestamp, deviceId: deviceId, timestamp: timestamp };
  if (taskCount !== null) m.taskCount = taskCount;
  return m;
}

function folder_() {
  const found = DriveApp.getFoldersByName(FOLDER_NAME);
  return found.hasNext() ? found.next() : DriveApp.createFolder(FOLDER_NAME);
}

/** This phone's backup files, newest first. */
function files_(folder, deviceId) {
  const out = [];
  const it = folder.getFiles();
  while (it.hasNext()) {
    const f = it.next();
    const name = f.getName();
    if (name.indexOf(deviceId + '__') === 0 && name.slice(-5) === '.json') out.push(f);
  }
  out.sort(function (a, b) { return a.getName() < b.getName() ? 1 : -1; });
  return out;
}

function prune_(folder, deviceId) {
  files_(folder, deviceId).slice(KEEP_PER_DEVICE).forEach(function (f) { f.setTrashed(true); });
}
