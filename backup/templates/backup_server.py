#!/usr/bin/env python3
"""
Eisenhower Matrix: backup server for your own computer

Saves the app's backups as .json files in a folder on YOUR computer. Nothing
passes through the app's developer. Needs only Python 3 (no extra packages).
Setup steps: https://willtoforge.com/eisenhower-matrix/backup/connect/

    python3 backup_server.py --key YOUR-LONG-RANDOM-KEY --folder "PATH/TO/FOLDER"

Point --folder at a folder inside Google Drive for desktop (or Dropbox, OneDrive...)
and every backup also lands in that cloud drive.

The app only talks to https:// addresses, so put the server behind HTTPS, for
example with Tailscale (tailscale serve 8787) or Cloudflare Tunnel
(cloudflared tunnel --url http://localhost:8787). See the setup page.
"""
import argparse
import hmac
import json
import os
import re
import sys
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEEP_PER_DEVICE = 30
MAX_BODY = 50 * 1024 * 1024
SAFE = re.compile(r'[^A-Za-z0-9_.-]')


def safe_id(value):
    return SAFE.sub('', str(value or ''))[:100]


def file_name(device_id, timestamp):
    return f'{device_id}__{timestamp.replace(":", "-")}.json'


def timestamp_of(name, device_id):
    stamp = name[len(device_id) + 2:-5]
    return re.sub(r'T(\d\d)-(\d\d)-(\d\d)', r'T\1:\2:\3', stamp)


class Handler(BaseHTTPRequestHandler):
    key = ''
    folder = '.'
    server_version = 'EisenhowerBackup/1'

    def files(self, device_id):
        prefix = device_id + '__'
        names = [n for n in os.listdir(self.folder) if n.startswith(prefix) and n.endswith('.json')]
        return sorted(names, reverse=True)

    def send(self, status, value):
        body = json.dumps(value).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorised(self):
        given = self.headers.get('Authorization', '')
        if hmac.compare_digest(given.encode(), f'Bearer {self.key}'.encode()):
            return True
        self.send(401, {'error': 'Wrong or missing API key'})
        return False

    def route(self):
        path = self.path.split('?', 1)[0]
        parts = [unquote(p) for p in path.split('/') if p]
        if parts[:2] != ['api', 'backup']:
            return None
        return parts[2:]

    def do_GET(self):
        rest = self.route()
        if rest is None:
            return self.send(404, {'error': 'Not found'})
        if not self.authorised():
            return
        if len(rest) == 2 and rest[1] == 'history':
            device_id = safe_id(rest[0])
            return self.send(200, [
                {'id': n[:-5], 'deviceId': device_id, 'timestamp': timestamp_of(n, device_id)}
                for n in self.files(device_id)
            ])
        if len(rest) == 1:
            device_id = safe_id(rest[0])
            names = self.files(device_id)
            if not names:
                return self.send(404, {'error': 'No backup for this device ID yet'})
            with open(os.path.join(self.folder, names[0]), 'rb') as f:
                body = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return self.send(404, {'error': 'Not found'})

    def read_body(self):
        """The request body, plain or chunked (tunnels may send either); None if too large."""
        if 'chunked' in self.headers.get('Transfer-Encoding', '').lower():
            data = b''
            while True:
                size = int(self.rfile.readline().split(b';')[0].strip() or b'0', 16)
                if size == 0:
                    self.rfile.readline()
                    return data
                data += self.rfile.read(size)
                self.rfile.readline()
                if len(data) > MAX_BODY:
                    return None
        length = int(self.headers.get('Content-Length') or 0)
        if length > MAX_BODY:
            return None
        return self.rfile.read(length)

    def do_POST(self):
        rest = self.route()
        if rest != []:
            return self.send(404, {'error': 'Not found'})
        if not self.authorised():
            return
        raw = self.read_body()
        if raw is None:
            return self.send(413, {'error': 'Backup too large'})
        try:
            body = json.loads(raw)
        except ValueError:
            return self.send(400, {'error': 'Not JSON'})
        device_id = safe_id(body.get('deviceId') if isinstance(body, dict) else '')
        if not device_id or not isinstance(body.get('tasks'), list):
            return self.send(400, {'error': 'Not a backup'})
        timestamp = str(body.get('timestamp') or '')
        if not re.fullmatch(r'[0-9TZ:.+-]{10,40}', timestamp):
            return self.send(400, {'error': 'Bad timestamp'})
        name = file_name(device_id, timestamp)
        tmp = os.path.join(self.folder, name + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(body, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(self.folder, name))
        for old in self.files(device_id)[KEEP_PER_DEVICE:]:
            os.remove(os.path.join(self.folder, old))
        print(f'Saved {name} ({len(body["tasks"])} tasks)', flush=True)
        return self.send(200, {'id': name[:-5], 'deviceId': device_id, 'timestamp': timestamp,
                               'taskCount': len(body['tasks'])})

    def do_DELETE(self):
        rest = self.route()
        if rest is None or len(rest) != 2:
            return self.send(404, {'error': 'Not found'})
        if not self.authorised():
            return
        device_id = safe_id(rest[0])
        name = file_name(device_id, rest[1])
        path = os.path.join(self.folder, name)
        if safe_id(name) != name or not os.path.exists(path):
            return self.send(404, {'error': 'No such backup'})
        os.remove(path)
        return self.send(200, {'ok': True})

    def log_message(self, fmt, *args):
        pass  # keep the window quiet; saves are printed above


def main():
    parser = argparse.ArgumentParser(description='Backup server for the Eisenhower Matrix app')
    parser.add_argument('--key', required=True, help='API key: the same text you enter as API Key in the app (20+ characters)')
    parser.add_argument('--folder', default='eisenhower-backups', help='Folder to save backups in')
    parser.add_argument('--port', type=int, default=8787)
    args = parser.parse_args()
    if len(args.key) < 20:
        sys.exit('Use a key of at least 20 characters.')
    os.makedirs(args.folder, exist_ok=True)
    Handler.key = args.key
    Handler.folder = os.path.abspath(args.folder)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Saving backups to {Handler.folder}')
    print(f'Listening on http://localhost:{args.port}  (put HTTPS in front of it, see the setup page)')
    print('Press Ctrl+C to stop.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
