import cgi
import os
import http.server
import socketserver


PORT = 8081

Handler = http.server.SimpleHTTPRequestHandler

class FileUploadHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     }
        )
        fileitem = form['file']

        if fileitem.filename:
            with open(os.path.join('server/upload', fileitem.filename), 'wb') as f:
                f.write(fileitem.file.read())

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes('<html><body><h1>File uploaded!</h1></body></html>', 'utf-8'))
        else:
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes('<html><body><h1>Error uploading file</h1></body></html>', 'utf-8'))


class myhandler(http.server.SimpleHTTPRequestHandler, FileUploadHandler):
    def comfirm_request(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self) -> None:
        self.comfirm_request()
        self.wfile.write(open("index.html", "rb").read())
        
Handler = myhandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()



PORT = 8080



