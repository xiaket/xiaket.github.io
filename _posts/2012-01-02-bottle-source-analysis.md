---
title:  "Bottle对HTTP请求的处理"
date:   2012-01-02 15:43 +0800
ref:    bottle-source-analysis
---

最近玩[Bottle](http://bottlepy.org/)这个框架, 分析了一下它的源码, 顺便也理一下它是怎么处理HTTP请求的.

### 代码结构

我们先分析下`bottle.py`的代码结构. 这个单文件的框架有2900多行, 大致结构如下(手头的版本是0.10.7):

1. 0000-0140: 模块载入, 兼容性调整
1. 0140-0200: 逻辑无关的工具函数和工具类定义
1. 0200-0240: 异常定义. 需要注意的是, 不需要消息体的HTTP响应, 例如HTTP重定向之类, 在bottle中也被处理成一种异常.
1. 0240-0520: URL映射相关逻辑, 包括若干个路由异常的定义.
1. 0520:0860: 主Bottle类的定义.
1. 0860-1440: 装HTTP请求和响应的类的定义. 微型框架啥都可以省省, 但是这个如果再省, 就不能被称为是框架了.
1. 1440-1570: 各种插件.
1. 1570-1800: 各种数据结构.
1. 1800-2050: 乱七八糟的小函数.
1. 2050-2280: 框架虽小, 兼容的服务器倒真不少...
1. 2280-2450: 应用控制, 也挺乱的, 两个用来载入app, 一个起server, 还有一个用来自动重启server(这个都有啊喂, 你真是微型框架咩).
1. 2450-2830: 模板渲染及处理, 兼容的模板系统也不少.
1. 2830-EOF : 变量定义及一些实例化, 以及起内置服务器的main函数.

由于有实例化的部分, 我们得先看看这段. 一旦你要从bottle.py中引入一个名字到你自己的模块, 这些代码就得执行一遍. 除了那些对变量的定义外, 这一段做了下面几件事情:

<pre class="code" data-lang="python"><code>
def make_default_app_wrapper(name):
    ''' Return a callable that relays calls to the current default app. '''
    @functools.wraps(getattr(Bottle, name))
    def wrapper(*a, **ka):
        return getattr(app(), name)(*a, **ka)
    return wrapper

for name in '''route get post put delete error mount
               hook install uninstall'''.split():
    globals()[name] = make_default_app_wrapper(name)
    url = make_default_app_wrapper('get_url')
    del name

#: A thread-safe instance of :class:`Request` representing the `current` request.
request = Request()

#: A thread-safe instance of :class:`Response` used to build the HTTP response.
response = Response()

#: A thread-safe namespace. Not used by Bottle.
local = threading.local()

# Initialize app stack (create first empty Bottle app)
# BC: 0.6.4 and needed for run()
app = default_app = AppStack()
app.push()
</code></pre>

前面这段修改`globals()`是用`make_default_app_wrapper`这个函数将`Bottle`中的这些装饰器放到全局命名空间里来. 例如, 你原本需要写`@app.get`, 现在写成`@get`就行了. 后面这段注释已经说得很明白了, 我就不再多说.

### 线程初始化

为了分析HTTP请求的处理. 我们从wsgi脚本开始看. 我本地一个wsgi脚本的内容如下:

<pre class="code" data-lang="python"><code>
#coding=utf-8
import sys


sys.path.append('/home/apache/suisuinian')

from suisuinian.views import app as application
</code></pre>

这一段一定程度上模仿了`Django`的将项目目录加入`sys.path`的做法. `Bottle`官方文档里面的做法是将当前工作路径切到wsgi脚本所在的文件夹, 这一点, 虽然我完全能够理解其目的, 我个人不太欣赏.

我们就从这儿开始我们的旅程, apache重启后, wsgi线程还没有启动. 这时, 我们向服务器发起一个HTTP请求, 则会执行这个wsgi脚本. 这个脚本做的事情不外设置路径和从视图函数中导入`application`这个对象. 视图函数是这么写的:

<pre class="code" data-lang="python"><code>
from bottle import app

app = app()

@app.get('/test')
def test():
    # display a test string.
    return 'test'
</code></pre>

这一段代码从`bottle.py`中拿出`AppStack`, 并从中拿出初始化过的`Bottle`实例, 再重命名为`app`, 我们首先看看`AppStack`的具体逻辑:

<pre class="code" data-lang="python"><code>
class AppStack(list):
    """ A stack-like list. Calling it returns the head of the stack. """

    def __call__(self):
        """ Return the current default application. """
        return self[-1]

    def push(self, value=None):
        """ Add a new :class:`Bottle` instance to the stack """
        if not isinstance(value, Bottle):
            value = Bottle()
            self.append(value)
        return value
</code></pre>

前面说了, 在从`bottle.py`导出模块时就会执行一段代码, 包括`AppStack`的实例化和对其进行`push`操作. `AppStack`的实例化就是对一个列表的实例化, 参数为空, 所以此时列表也为空. 进行`push`操作时, 如果参数和我们现在一样为空, 则会实例化一个新的`Bottle`对象. 最后, 我们将这个对象(或者命令行下给出的另一个`Bottle`实例)放到栈顶. 如我们前面的代码所示, 我们会在视图中调用`AppStack`的`__call__`方法, 拿到这个默认的`Bottle`实例.

### Bottle的实例化

接下来, 我们看看`Bottle`的实例化过程具体做了什么:

<pre class="code" data-lang="python"><code>
class Bottle(object):
    """ WSGI application """
    def __init__(self, catchall=True, autojson=True, config=None):
        self.routes = [] # List of installed :class:`Route` instances.
        self.router = Router() # Maps requests to :class:`Route` instances.
        self.plugins = [] # List of installed plugins.

        self.error_handler = {}
        #: If true, most exceptions are catched and returned as :exc:`HTTPError`
        self.config = ConfigDict(config or {})
        self.catchall = catchall
        #: An instance of :class:`HooksPlugin`. Empty by default.
        self.hooks = HooksPlugin()
        self.install(self.hooks)
        if autojson:
            self.install(JSONPlugin())
        self.install(TemplatePlugin())
</code></pre>

先从整体看看这个初始化的过程. 整个过程中定义了若干个容器来放`app`的属性, 包括插件, URL映射表等等. `Bottle`的实例化过程中实例化了一个`Router`对象. `Router`的核心实例化代码为:

<pre class="code" data-lang="python"><code>
class Router(object):
    def __init__(self):
        self.rules    = {} # A {rule: Rule} mapping
        self.builder  = {} # A rule/name->build_info mapping
        self.static   = {} # Cache for static routes: {path: {method: target}}
        self.dynamic  = [] # Cache for dynamic routes. See _compile()
        self.filters = {'re': self.re_filter, 'int': self.int_filter,
                        'float': self.float_filter, 'path': self.path_filter}
</code></pre>

可以看出, `Router`就是URL映射器了.

另外, `Bottle`初始化过程中还实例化了一个`ConfigDict`对象. 这个对象是在`dict`对象上加了一些扩展, 能够用类似类属性的方式来访问字典的值. 具体来说还是一个装配置的容器. 另外, `Bottle`的实例化完成后, 装载了三个插件(`Hooks`, `JSON`和模板).

### 路由表的载入

为了避免思绪混乱, 我们在继续之前, 先看看目前做了哪些事情:

1. Apache找到我们的wsgi脚本.
1. wsgi脚本开始从我们的视图函数中载入app这个对象.
1. 我们的视图函数开始载入bottle.py中的对象.
1. bottle.py完成初始化.

好吧, 到现在, 我们已经完成`bottle.py`的初始化了, 我们的视图函数可以正常地载入`app`这个对象了. 接下来, 它兴致盎然地完成了`app = app()`这一步. 我们之前看过`AppStack`的代码, 知道这一步会用一个`Bottle`对象替换一个`AppStack`对象. 用这种名字替换是会让人引起混乱的, 这一方面是我的错, 另一方面, 代码中这一点也够混乱. 为了让你看得更清楚一点, 我将视图函数的内容改写在下面:

<pre class="code" data-lang="python"><code>
from bottle import app as appstack_obj

app = appstack_obj()

@app.get('/test')
def test():
    # display a test string.
    return "test"
</code></pre>

到这儿, 我们已经处理完了`app`相关的逻辑, 但是在我们的wsgi脚本完成对`app`这个对象的载入前, python还会处理后面函数的初始化(虽然没有执行). 在这个过程中, url映射关系被放进了`Bottle`对象中. 具体我们来看`app.get`方法. 这个方法要和`app.route`一起看:

<pre class="code" data-lang="python"><code>
def get(self, path=None, method='GET', **options):
    """ Equals :meth:`route`. """
    return self.route(path, method, **options)

def route(self, path=None, method='GET', callback=None, name=None,
            apply=None, skip=None, **config):
    if callable(path): path, callback = None, path
    plugins = makelist(apply)
    skiplist = makelist(skip)

    def decorator(callback):
        # TODO: Documentation and tests
        if isinstance(callback, basestring): callback = load(callback)
        for rule in makelist(path) or yieldroutes(callback):
            for verb in makelist(method):
                verb = verb.upper()
                route = Route(self, rule, verb, callback, name=name,
                                plugins=plugins, skiplist=skiplist, **config)
                self.routes.append(route)
                self.router.add(rule, verb, route, name=name)
                if DEBUG: route.prepare()
        return callback
    return decorator(callback) if callback else decorator
</code></pre>

按照我们的视图函数, 传递给`route`这个方法的参数中`path`是`'/test'`, `method`是`'GET'`, `callback`是`None`. 到`decorator`时, `callback`是被装饰器包裹的函数, `test`. 后面基本是顺理成章的了: 实例化一个`Route`对象, 并将其加入`app`的路由表.

到这儿, 我们终于走到了wsgi脚本的结尾. 线程初始化完毕, 可以开始接受请求了.

### HTTP请求的处理

HTTP请求是通过Bottle对象的__call__方法完成的:

<pre class="code" data-lang="python"><code>
def __call__(self, environ, start_response):
    ''' Each instance of :class:'Bottle' is a WSGI application. '''
    return self.wsgi(environ, start_response)
</code></pre>

实际上是调用了`self.wsgi`方法, 去掉异常处理后, 其核心代码如下:

<pre class="code" data-lang="python"><code>
def wsgi(self, environ, start_response):
    """ The bottle WSGI-interface. """
    environ['bottle.app'] = self
    request.bind(environ)
    response.bind()
    out = self._cast(self._handle(environ), request, response)
    # rfc2616 section 4.3
    if response._status_code in (100, 101, 204, 304)\
    or request.method == 'HEAD':
        if hasattr(out, 'close'): out.close()
        out = []
    start_response(response._status_line, list(response.iter_headers()))
    return out
</code></pre>

`request`这个变量是我们之前说过的, `bottle.py`文件结尾处实例化的`LocalRequest`对象. 具体的`bind`方法实际上执行了`BaseRequest`这个类的初始化方法:

<pre class="code" data-lang="python"><code>
class BaseRequest(DictMixin):
    """ A wrapper for WSGI environment dictionaries that adds a lot of
            convenient access methods and properties. Most of them are read-only."""

    #: Maximum size of memory buffer for :attr:`body` in bytes.
    MEMFILE_MAX = 102400
    #: Maximum number pr GET or POST parameters per request
    MAX_PARAMS  = 100

    def __init__(self, environ):
        """ Wrap a WSGI environ dictionary. """
        #: The wrapped WSGI environ dictionary. This is the only real attribute.
        #: All other attributes actually are read-only properties.
        self.environ = environ
        environ['bottle.request'] = self
</code></pre>

好似除了将初始化参数提供给一个类变量, 并添加了一个属性外, 没做啥事情. 字典中的值都是按需读取的. `DictMixin`提供一个字典的骨架, 具体可以参考python官方文档. 顺口说一句, 这儿的`MAX_PARAMS`设置能够避免前几天热议的hash碰撞攻击.

`response.bind()`的作用也就是实例化一个`BaseResponse`对象, 这儿还没什么值, 讨论从略.

我们先看看要给`_cast`方法传递参数的`_handle`方法:

<pre class="code" data-lang="python"><code>
def _handle(self, environ):
    try:
        route, args = self.router.match(environ)
        environ['route.handle'] = environ['bottle.route'] = route
        environ['route.url_args'] = args
        return route.call(**args)
    except HTTPResponse, r:
        return r
    except RouteReset:
        route.reset()
        return self._handle(environ)
    except (KeyboardInterrupt, SystemExit, MemoryError):
        raise
    except Exception, e:
        if not self.catchall: raise
        stacktrace = format_exc(10)
        environ['wsgi.errors'].write(stacktrace)
        return HTTPError(500, "Internal Server Error", e, stacktrace)
</code></pre>

这一段里用`Router`实例做了url匹配, 于是再跟过去看看:

<pre class="code" data-lang="python"><code>
def match(self, environ):
    ''' Return a (target, url_agrs) tuple or raise HTTPError(400/404/405). '''
    path, targets, urlargs = environ['PATH_INFO'] or '/', None, {}
    if path in self.static:
        targets = self.static[path]
    else:
        for combined, rules in self.dynamic:
            match = combined.match(path)
            if not match: continue
            getargs, targets = rules[match.lastindex - 1]
            urlargs = getargs(path) if getargs else {}
            break

    if not targets:
        raise HTTPError(404, "Not found: " + repr(environ['PATH_INFO']))
    method = environ['REQUEST_METHOD'].upper()
    if method in targets:
        return targets[method], urlargs
    if method == 'HEAD' and 'GET' in targets:
        return targets['GET'], urlargs
    if 'ANY' in targets:
        return targets['ANY'], urlargs
    allowed = [verb for verb in targets if verb != 'ANY']
    if 'GET' in allowed and 'HEAD' not in allowed:
        allowed.append('HEAD')
    raise HTTPError(405, "Method not allowed.",
                    header=[('Allow',",".join(allowed))])
</code></pre>

这一段虽然比较长, 逻辑也比较复杂, 但是在官方文档的1.2.4节路由顺序(Routing Order)中已经有讲解, 此文从略. 匹配到适当的处理函数后, `_handle`函数中调用了对应的函数并返回.

对`_cast`方法有兴趣的同学可以自行围观代码, 但是这个方法基本是在查漏补缺了. 从`_cast`方法中出来后, 我们就调用`start_response`并返回内容了. 至此, bottle已完成了对一个最简单的HTTP请求的处理.
