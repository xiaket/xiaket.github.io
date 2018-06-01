---
title:  "Astng导致的纠结问题一例"
date:   2012-03-06 16:44 +0800
lang: zh
ref:    astng-and-new
---

今天干活时出了件蹊跷的事情, 我在调试一个功能时随手写了一个脚本来测试. 脚本的名字是new.py, 内容如下:

```python
class A(object):
    def a(self, it):
        print it
        return 0


a = A()
if a.a("test") == 0:
    print "ok"
```

这个脚本挺简单, 具体逻辑不解释了. 但是在我的机器上运行时输出却比较奇怪, 内容打印了两次:

```bash
[xiaket@bolt:~]python new.py
test
ok
test
ok
```

然后就纳闷了. 偶首先找来LD, 他给我测了下, 在他的机器上没问题. 我自己也另外找了机器, 都是没问题的. 于是肯定是我本地环境的问题. 然后我看了下我的本地环境变量, 里面除了设置PYTHONPATH外没干别的事情:

```bash
[xiaket@bolt:~]export | grep python
declare -x PYTHONPATH="/home/xiaket/.xiaket/python:/home/xiaket/.xiaket/python/lib:/home/xiaket/.xiaket/python:/home/xiaket/.xiaket/python/lib"
```

那么应该不是环境变量之类的问题. 老老实实打开调试:

```python
# installing zipimport hook
import zipimport # builtin
# installed zipimport hook
# /usr/lib/python2.6/site.pyc has bad mtime
import site # from /usr/lib/python2.6/site.py
# can't create /usr/lib/python2.6/site.pyc
# /usr/lib/python2.6/os.pyc matches /usr/lib/python2.6/os.py
import os # precompiled from /usr/lib/python2.6/os.pyc
import errno # builtin
import posix # builtin
# /usr/lib/python2.6/posixpath.pyc matches /usr/lib/python2.6/posixpath.py
import posixpath # precompiled from /usr/lib/python2.6/posixpath.pyc
# /usr/lib/python2.6/stat.pyc matches /usr/lib/python2.6/stat.py
import stat # precompiled from /usr/lib/python2.6/stat.pyc
# /usr/lib/python2.6/genericpath.pyc matches /usr/lib/python2.6/genericpath.py
import genericpath # precompiled from /usr/lib/python2.6/genericpath.pyc
# /usr/lib/python2.6/warnings.pyc matches /usr/lib/python2.6/warnings.py
import warnings # precompiled from /usr/lib/python2.6/warnings.pyc
# /usr/lib/python2.6/linecache.pyc matches /usr/lib/python2.6/linecache.py
import linecache # precompiled from /usr/lib/python2.6/linecache.pyc
# /usr/lib/python2.6/types.pyc matches /usr/lib/python2.6/types.py
import types # precompiled from /usr/lib/python2.6/types.pyc
# /usr/lib/python2.6/UserDict.pyc matches /usr/lib/python2.6/UserDict.py
import UserDict # precompiled from /usr/lib/python2.6/UserDict.pyc
# /usr/lib/python2.6/_abcoll.pyc matches /usr/lib/python2.6/_abcoll.py
import _abcoll # precompiled from /usr/lib/python2.6/_abcoll.pyc
# /usr/lib/python2.6/abc.pyc matches /usr/lib/python2.6/abc.py
import abc # precompiled from /usr/lib/python2.6/abc.pyc
# /usr/lib/python2.6/copy_reg.pyc matches /usr/lib/python2.6/copy_reg.py
import copy_reg # precompiled from /usr/lib/python2.6/copy_reg.pyc
# /home/xiaket/new.pyc matches /home/xiaket/new.py
import new # precompiled from /home/xiaket/new.pyc
test
ok
import encodings # directory /usr/lib/python2.6/encodings
# /usr/lib/python2.6/encodings/__init__.pyc matches /usr/lib/python2.6/encodings/__init__.py
import encodings # precompiled from /usr/lib/python2.6/encodings/__init__.pyc
# /usr/lib/python2.6/codecs.pyc matches /usr/lib/python2.6/codecs.py
import codecs # precompiled from /usr/lib/python2.6/codecs.pyc
import _codecs # builtin
# /usr/lib/python2.6/encodings/aliases.pyc matches /usr/lib/python2.6/encodings/aliases.py
import encodings.aliases # precompiled from /usr/lib/python2.6/encodings/aliases.pyc
# /usr/lib/python2.6/encodings/utf_8.pyc matches /usr/lib/python2.6/encodings/utf_8.py
import encodings.utf_8 # precompiled from /usr/lib/python2.6/encodings/utf_8.pyc
Python 2.6.6 (r266:84292, Nov 27 2010, 19:47:39)
[GCC 4.5.1] on linux2
Type "help", "copyright", "credits" or "license" for more information.
test
ok
# clear __builtin__._
# clear sys.path
# ... More lines omitted here ...
# cleanup ints: 18 unfreed ints
# cleanup floats
```

可见, 在前期调用中, new被import了一次, 由此导致了输出被打印两次的问题. new.py这个文件本身是python的一部分, 文件位置在/usr/lib/python2.6/new.py, 内容如下:

```python
"""Create new objects of various types.  Deprecated.

This module is no longer required except for backward compatibility.
Objects of most types can now be created by calling the type object.
"""
from warnings import warnpy3k
warnpy3k("The 'new' module has been removed in Python 3.0; use the 'types' "
            "module instead.", stacklevel=2)
del warnpy3k

from types import ClassType as classobj
from types import FunctionType as function
from types import InstanceType as instance
from types import MethodType as instancemethod
from types import ModuleType as module

# CodeType is not accessible in restricted execution mode
try:
    from types import CodeType as code
except ImportError:
    pass
```

从文件内容和注释我们可以看到, 这个文件只是为了兼容目的而存在的. 无论如何, 我们先删除这个文件, 也将/home/xiaket/new.py重命名一下, 看看哪儿会报错:

```
[xiaket@bolt:~]python t.py
'import site' failed; use -v for traceback
test
ok
```

python已经提示我们了. import site这一步有问题. 于是再次打开-v调试. 中间一段报错截取如下:

```python
'import site' failed; traceback:
Traceback (most recent call last):
  File "/usr/lib/python2.6/site.py", line 525, in <module>
    main()
  File "/usr/lib/python2.6/site.py", line 508, in main
    known_paths = addsitepackages(known_paths)
  File "/usr/lib/python2.6/site.py", line 288, in addsitepackages
    addsitedir(sitedir, known_paths)
  File "/usr/lib/python2.6/site.py", line 185, in addsitedir
    addpackage(sitedir, name, known_paths)
  File "/usr/lib/python2.6/site.py", line 155, in addpackage
    exec line
  File "<string>", line 1, in <module>
ImportError: No module named new
```

site.py是一个python模块. 直接往里面插代码打印调试信息, 找到了罪魁. 具体文件是logilab_astng-0.21.1-py2.6-nspkg.pth. 这个文件是我为了满足pylint的依赖关系而安装的一个包, 这个pth具体内容整理后如下:

```python
import sys, new, os

p = os.path.join(sys._getframe(1).f_locals['sitedir'], *('logilab',))
ie = os.path.exists(os.path.join(p,'__init__.py'))
m = not ie and sys.modules.setdefault('logilab',new.module('logilab'))
mp = (m or []) and m.__dict__.setdefault('__path__',[])
(p not in mp) and mp.append(p)
```

这段具体做了什么我懒得跟了. 我很烦这种把一个公司当做目录来搞的行为, 我重命名后跑pylint没啥问题, 于是就删除了这个文件. 另外把`logilab_common-0.56.0-py2.6-nspkg.pth`这个文件也干掉了, 处理完之后就没问题了.
