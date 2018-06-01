---
title:  "拓展python的SimpleHTTPServer"
date:   2011-06-27 21:22 +0800
lang: zh
ref:    extending-simplehttpserver
---

经常我们需要给人传文件. 对于我们这些在各地各网段有机器登录权限的人而言, 直接给人传文件并不一定是最佳的选择. 更理想的情况还是找到对方的IP, 根据对方的网络环境来把要传的文件放到一台更接近的机器上, 然后起一个python的`HTTPServer`, 开一个端口来传文件. 要实现这一点实际上是很容易的:

```bash
python -m SimpleHTTPServer
```

这样就在这台服务器上开了一个8000端口, 提供当前目录下的内容.

这样的处理方式虽然简单, 但是有些问题却比较讨厌:

* 每次端口都是8000, 不太好. 而且8000这个端口本身也算是一个周知端口.
* 传文件不能中断后续传. 如果文件传了一半网络有问题就得重来.
* 日志比较丑, 包括了不少不必要的traceback.
* 文件传送完毕后没有提示, 不知道什么时候可以关.
* 每次开了服务后还要自己手动拼url给对方.

为解决这些问题, 我们可以通过写一个简单的python脚本来拓展python自带的`SimpleHTTPServer`的功能. 我们的出发点是python官方文档中的例子:

```python
def run(server_class=BaseHTTPServer.HTTPServer,
        handler_class=BaseHTTPServer.BaseHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()
```

端口的问题可以用`random.randint`来找一个随机端口, 不提. 开服务后加一些代码能够把当前目录下的文件列出来. 并给出拼好的url, 这些修改都比较简单:

```python
def main(port, server_class=NotracebackServer,
            handler_class=PartialContentHandler):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    port = randint(20000, 50000)
    ip = socket.gethostbyname(socket.gethostname())
    print "serving on: http://%s:%s/" % (ip, port)
    print "===== local files ====="
    cwd = os.getcwd()
    for f in os.listdir(cwd):
        if f == sys.argv[0] or f.startswith("."):
            continue
        fullpath = os.path.join(cwd, f)
        if os.path.isfile(fullpath):
            print "link: http://%s:%s/%s" % (ip, port, f)
    print "===== start logging =====n"
    main(port=port)
```

这儿main中的参数我们后面会谈到. 这段代码的输出类似:

```
[xiaket@bolt:~]httpd.py
serving on: http://10.0.2.15:34451/
===== local files =====
link: http://10.0.2.15:34451/file.tgz
===== start logging =====
```

下面主要讲给`SimpleHTTPServer`添加续传的功能. 这是一个标准HTTP功能, 不过SimpleHTTPServer没有实现这一点, 这一点具体详情可以参考[相关RFC](www.ietf.org/rfc/rfc2068.txt). 另外, 我们可以用wget, 找一台支持续传功能的httpd, 把具体的HTTP通讯中的request和response打印出来:

```
[xiaket@bolt:~]wget -d -nv -c http://mirrors.163.com/slackware/slackware-13.0-iso/slackware-13.0-install-d1.iso -O out
Setting --no (verbose) to 0
Setting --continue (continue) to 1
Setting --output-document (outputdocument) to out
DEBUG output created by Wget 1.12 on linux-gnu.

URI encoding = “UTF-8”
Caching mirrors.163.com => 123.58.173.89 123.58.173.106
Created socket 4.
Releasing 0x080bf3d8 (new refcount 1).

---request begin---
GET /slackware/slackware-13.0-iso/slackware-13.0-install-d1.iso HTTP/1.0
User-Agent: Wget/1.12 (linux-gnu)
Accept: */*
Host: mirrors.163.com
Connection: Keep-Alive

---request end---

---response begin---
HTTP/1.1 200 OK
Server: nginx
Date: Mon, 27 Jun 2011 09:48:46 GMT
Content-Type: application/octet-stream
Connection: keep-alive
Content-Length: 620077056
Last-Modified: Wed, 26 Aug 2009 16:10:47 GMT
Accept-Ranges: bytes

---response end---
HTTP/1.1 200 OK
Server: nginx
Date: Mon, 27 Jun 2011 09:48:46 GMT
Content-Type: application/octet-stream
Connection: keep-alive
Content-Length: 620077056
Last-Modified: Wed, 26 Aug 2009 16:10:47 GMT
Accept-Ranges: bytes
Registered socket 4 for persistent reuse.
```

接下来, 我们只需依样画葫芦, 解析传过来的request, 给出一样的response的就行了. 负责处理GET请求的函数是`SimpleHTTPRequestHandler`类里的`do_GET`方法. 这个类比较简单:

```python
def do_GET(self):
    """Serve a GET request."""
    f = self.send_head()
    if f:
        self.copyfile(f, self.wfile)
        f.close()
```

主要逻辑是处理完`header`后拿到一个文件对象, 然后往`self.wfile`里面复制文件(这样就写到客户端了). 主要的处理逻辑还是在`send_head`里:

```python
def send_head(self):
    """Common code for GET and HEAD commands.

    This sends the response code and MIME headers.

    Return value is either a file object (which has to be copied
    to the outputfile by the caller unless the command was HEAD,
    and must be closed by the caller under all circumstances), or
    None, in which case the caller has nothing further to do.

    """
    path = self.translate_path(self.path)
    f = None
    if os.path.isdir(path):
        if not self.path.endswith('/'):
            # redirect browser - doing basically what apache does
            self.send_response(301)
            self.send_header("Location", self.path + "/")
            self.end_headers()
            return None
        for index in "index.html", "index.htm":
            index = os.path.join(path, index)
            if os.path.exists(index):
                path = index
                break
        else:
            return self.list_directory(path)
    ctype = self.guess_type(path)
    try:
        # Always read in binary mode. Opening files in text mode may cause
        # newline translations, making the actual size of the content
        # transmitted *less* than the content-length!
        f = open(path, 'rb')
    except IOError:
        self.send_error(404, "File not found")
        return None
    self.send_response(200)
    self.send_header("Content-type", ctype)
    fs = os.fstat(f.fileno())
    self.send_header("Content-Length", str(fs[6]))
    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
    self.end_headers()
    return f
```

首先拿到GET请求的实际路径, 然后如果这个路径是个文件夹, 就做一些逻辑, 例如显示`index.html`和显示文件列表等. 对于我的传文件的需求, 这些功能是不必要的, 于是砍掉, 留一个提示文件找不到的404就行. 后面马上就到了返回状态码200, 这个可不行. 按照RFC的要求, 续传时返回的状态码应是206. 实际上, 做这种续传请求需要一个特殊的header, Range. 为此, 我们在这儿加一个逻辑判断捕获这个header:

```python
def send_head(self):
    """
    added support for partial content. i'm not surprised if http HEAD
    method would fail.
    """
    path = self.translate_path(self.path)
    f = None
    if os.path.isdir(path):
        # oh, we do not support directory listing.
        self.send_error(404, "File not found")
        return None

    ctype = self.guess_type(path)
    try:
        f = open(path, 'rb')
    except IOError:
        self.send_error(404, "File not found")
        return None
    if self.headers.get("Range"):
        # partial content all treated here.
        # we do not support If-Range request.
        # range could only be of the form:
        #   Range: bytes=9855420-
        start = self.headers.get("Range")
        try:
            pos = int(start[6:-1])
        except ValueError:
            self.send_error(400, "bad range specified.")
            f.close()
            return None
```

按照HTTP RFC的要求, Range应可以像python的列表一样给定范围, 不过增加这种范围支持只会给下载工具带来方便(我们不喜欢迅雷!), 因此此处特意只支持到结尾的Range请求. 后面就比较容易了, 拼字符串而已:

```python
self.send_response(206)
self.send_header("Content-type", ctype)
self.send_header("Connection", "keep-alive")
fs = os.fstat(f.fileno())
full = fs.st_size
self.send_header("Content-Length", str(fs[6] - pos))
self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
start = start.replace("=", " ")
self.send_header("Content-Range", "%s%s/%s" % (start, full-1, full))
self.end_headers()
f.seek(pos)
return f
```

后面的处理普通GET请求代码和原来的`send_head`一致, 就不贴了. 为了给传送完毕增加一条日志, 并让整个代码结构更合理, 我定义了一个新函数`mycopy`来处理原理的copyfile的逻辑:

```python
class PartialContentHandler(SimpleHTTPRequestHandler):
    def mycopy(self, f):
        """
        This would do the actual file tranfer. if client terminated transfer,
        we would log it.
        """
        try:
            self.copyfile(f, self.wfile)
            self.log_message('"%s" %s', self.requestline, "req finished.")
        except socket.error:
            self.log_message('"%s" %s', self.requestline, "req terminated.")
        finally:
            f.close()
        return None

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.mycopy(f)
```

`PartialContentHandler`里除了这两个已列出的方法外, 还有刚才我们提到的`send_head`方法. 这儿的`log_message`方法是在基类`BaseHTTPServer`中定义的.

另外, 为了隐藏客户端中断传输时的`traceback`, 我们需要重载`HTTPServer`类中的`handle_error`方法. 直接写一个pass就行了.

完整的代码可以从[这儿](https://github.com/xiaket/etc/blob/master/bin/httpd-download.py)获得

完整的输出演示如下:

```
[xiaket@bolt:~]python httpd.py
serving on: http://10.0.2.15:27708/
===== local files =====
link: http://10.0.2.15:27708/bigfile
link: http://10.0.2.15:27708/jobs
===== start logging =====

bolt.netease.com - - [27/Jun/2011 18:52:39] "GET /jobs HTTP/1.0" 200 -
bolt.netease.com - - [27/Jun/2011 18:52:39] "GET /jobs HTTP/1.0" req finished.
bolt.netease.com - - [27/Jun/2011 18:52:55] "GET /bigfile HTTP/1.0" 200 -
bolt.netease.com - - [27/Jun/2011 18:52:56] "GET /bigfile HTTP/1.0" req terminated.
bolt.netease.com - - [27/Jun/2011 18:53:05] "GET /bigfile HTTP/1.0" 206 -
bolt.netease.com - - [27/Jun/2011 18:53:05] "GET /bigfile HTTP/1.0" req finished.
```
