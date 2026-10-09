"""Caching reverse proxy for the Netgear Orbi web panel.

The Orbi SPA ships a ~5-6 MB JavaScript bundle that often fails to load over a
weak or lossy Wi-Fi link. This proxy caches static files on disk after the first
successful download and forwards everything else (including /dniapi/*) to the router.
It also serves index.html for /conflict, a route the router itself answers with 404.

Usage:
    python orbi_proxy.py                      # router 10.0.0.1, panel at http://127.0.0.1:8088
    ORBI_HOST=192.168.1.1 PROXY_PORT=8090 python orbi_proxy.py

Listens on 127.0.0.1 only. Delete the ./cache folder after a firmware update.
"""
import http.server, http.client, socketserver, os, sys, time, threading, mimetypes, urllib.parse
UP_HOST = os.environ.get('ORBI_HOST', '10.0.0.1')
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
PORT = int(os.environ.get('PROXY_PORT', '8088'))
STATIC_EXT = ('.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.ico', '.json', '.map')
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade', 'host', 'accept-encoding', 'content-length'}
lock = threading.Lock()
def log(msg):
    with lock:
        sys.stdout.write(time.strftime('%H:%M:%S ') + msg + '\n'); sys.stdout.flush()
class H(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def cache_path(self):
        p = urllib.parse.urlparse(self.path).path
        if not p.lower().endswith(STATIC_EXT) or '..' in p: return None
        return os.path.join(CACHE, p.lstrip('/').replace('/', os.sep))
    def send_all(self, status, headers, body):
        self.send_response(status)
        for k, v in headers: self.send_header(k, v)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        if self.command != 'HEAD': self.wfile.write(body)
    def do_any(self):
        if self.command in ('GET', 'HEAD') and urllib.parse.urlparse(self.path).path.rstrip('/') == '/conflict':
            self.path = '/index.html'
        cp = self.cache_path() if self.command in ('GET', 'HEAD') else None
        if cp and os.path.isfile(cp):
            with open(cp, 'rb') as f: body = f.read()
            ct = mimetypes.guess_type(cp)[0] or 'application/octet-stream'
            if cp.endswith('.js'): ct = 'application/javascript'
            self.send_all(200, [('Content-Type', ct), ('Cache-Control', 'max-age=86400')], body)
            return
        n = int(self.headers.get('Content-Length') or 0)
        data = self.rfile.read(n) if n else None
        hdrs = {}
        for k, v in self.headers.items():
            if k.lower() in HOP: continue
            if k.lower() in ('origin', 'referer'):
                v = v.replace('127.0.0.1:%d' % PORT, UP_HOST).replace('localhost:%d' % PORT, UP_HOST)
            hdrs[k] = v
        hdrs['Host'] = UP_HOST
        if data is not None: hdrs['Content-Length'] = str(len(data))
        for attempt in range(3):
            try:
                c = http.client.HTTPConnection(UP_HOST, 80, timeout=90)
                c.request(self.command, self.path, body=data, headers=hdrs)
                r = c.getresponse(); body = r.read()
                rh = [(k, v) for k, v in r.getheaders() if k.lower() not in ('connection', 'transfer-encoding', 'content-length', 'keep-alive')]
                c.close()
                if cp and r.status == 200 and body:
                    os.makedirs(os.path.dirname(cp), exist_ok=True)
                    with open(cp, 'wb') as f: f.write(body)
                    log('CACHED %s (%d bytes)' % (self.path, len(body)))
                elif not cp:
                    log('%s %s -> %d %s' % (self.command, self.path, r.status, body[:120].decode('utf-8', 'replace').replace('\n', ' ')))
                self.send_all(r.status, rh, body)
                return
            except Exception as e:
                log('UPSTREAM ERR %s %s attempt %d: %s' % (self.command, self.path, attempt + 1, e))
                time.sleep(1)
        try: self.send_all(502, [('Content-Type', 'text/plain')], b'proxy upstream error')
        except Exception: pass
    do_GET = do_POST = do_HEAD = do_PUT = do_DELETE = do_OPTIONS = do_any
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True
if __name__ == '__main__':
    log('proxy on 127.0.0.1:%d -> %s cache=%s' % (PORT, UP_HOST, CACHE))
    S(('127.0.0.1', PORT), H).serve_forever()
