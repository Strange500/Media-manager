# -*- coding: utf-8 -*

from http.server import BaseHTTPRequestHandler, CGIHTTPRequestHandler, HTTPServer
from os import curdir, sep, remove,popen

from json_API import *


HTML_FILE_NAME = 'alive'
PORT_NUMBER = 80

# This class will handles any incoming request from the browser
class myHandler(CGIHTTPRequestHandler):
    def comfirm_request(self)->None:
        self.send_response(200)
        self.send_header('Content-type', 'application/json') 
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()

    
    def make_response(self) -> None:
        req_dic={
            "/alive" : lambda : self.comfirm_request() or self.wfile.write(bytes(alive(),encoding="utf-8")),
            "/space" : lambda : self.comfirm_request() or self.wfile.write(bytes(space(),encoding="utf-8")),
            "/restart" : lambda : self.comfirm_request() or self.wfile.write(bytes(restart(),encoding="utf-8"))
        }
        try:
            req_dic[self.path]()
        except KeyError:
            self.send_response(404, 'request means nothing: %s' % self.path)
    # Handler for the GET requests
    
    def do_GET(self):
        self.cgi_directories = ["/"]
        self.make_response()
        # if str(self.path)=="/":


        #     self.path = HTML_FILE_NAME
        
        # try:
        #     with open(curdir + sep + self.path, 'r',encoding="utf-8") as f:
        #         self.send_response(200)
        #         self.send_header('Content-type', 'text/html')
        #         self.end_headers()
        #         self.wfile.write(str(popen("python "+self.path).read()).encode('utf-8'))
        #     return
        # except IOError:
        #     self.send_error(404, 'File Not Found: %s' % self.path)

try:
    # Create a web server and define the handler to manage the incoming request
    
    print('Started httpserver on port %i.' % PORT_NUMBER)
    myHandler.cgi_directories= ["/"]
    #Wait forever for incoming http requests

    
    
    HTTPServer(('', PORT_NUMBER), myHandler).serve_forever()

except KeyboardInterrupt:
    print('Interrupted by the user - shutting down the web server.')
    server.socket.close()
    remove(HTML_FILE_NAME)