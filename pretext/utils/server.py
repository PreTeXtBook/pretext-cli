import threading
import random
import json
import socketserver
import socket
import os
import watchdog.events, watchdog.observers, time
from http.server import SimpleHTTPRequestHandler
import logging

# Get access to logger
log = logging.getLogger('ptxlogger')

# watchdog handler for watching changes to source
class HTMLRebuildHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self,callback):
        self.last_trigger_at = time.time()-5
        self.callback = callback
    def on_any_event(self,event):
        self.last_trigger_at = time.time()
        # only run callback once triggers halt for a second
        def timeout_callback(handler):
            time.sleep(1.5)
            if time.time() > handler.last_trigger_at + 1:
                handler.last_trigger_at = time.time()
                log.info("\nChanges to source detected.\n")
                handler.callback()
        threading.Thread(target=timeout_callback,args=(self,)).start()

# boilerplate to prevent overzealous caching by preview server, and
# avoid port issues
def binding_for_access(access="private"):
    if os.path.isfile("/home/user/.smc/info.json") or access=="public":
        return "0.0.0.0"
    else:
        return "localhost"
def url_for_access(access="private",port=8000):
    if os.path.isfile("/home/user/.smc/info.json"):
        project_id = json.loads(open('/home/user/.smc/info.json').read())['project_id']
        return f"https://cocalc.com/{project_id}/server/{port}/"
    elif access=='public':
        return f"http://{socket.gethostbyname(socket.gethostname())}:{port}"
    else:
        return f"http://localhost:{port}"
def serve_forever(directory,access="private",port=8000):
    log.info(f"Now starting a server to preview directory `{directory}`.\n")
    binding = binding_for_access(access)
    class RequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        """HTTP request handler with no caching"""
        def end_headers(self):
            self.send_my_headers()
            SimpleHTTPRequestHandler.end_headers(self)
        def send_my_headers(self):
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
    class TCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    looking_for_port = True
    while looking_for_port:
        try:
            with TCPServer((binding, port), RequestHandler) as httpd:
                looking_for_port = False
                url = url_for_access(access,port)
                log.info(f"Success! Open the below url in a web browser to preview the most recent build of your project.")
                log.info("    "+url)
                log.info("Use [Ctrl]+[C] to halt the server.\n")
                httpd.serve_forever()
        except OSError:
            log.warning(f"Port {port} could not be used.")
            port = random.randint(49152,65535)
            log.warning(f"Trying port {port} instead.\n")

def run_server(directory,access,port,watch_directory=None,watch_callback=lambda:None):
    binding = binding_for_access(access)
    threading.Thread(target=lambda: serve_forever(directory,access,port),daemon=True).start()
    if watch_directory is not None:
        log.info(f"\nWatching for changes in `{watch_directory}` ...\n")
        event_handler = HTMLRebuildHandler(watch_callback)
        observer = watchdog.observers.Observer()
        observer.schedule(event_handler, watch_directory, recursive=True)
        observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\nClosing server...")
        if watch_directory is not None: observer.stop()
    if watch_directory is not None: observer.join()