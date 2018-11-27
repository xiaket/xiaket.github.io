---
title:  "用python来编写vim脚本"
date:   2013-06-04 15:44 +0800
ref:    vim-python
---

之前我在网上找了个自动给python/sh脚本添加header的snippet, 一直在使用. 这个snippet大致是这样的:

<pre class="code" data-lang="vim"><code>
" python and shell script header.
function AddTitlePython()
    call setline(1, "#!/usr/bin/env python")
    call append(1, "#coding=utf-8")
    call append(2, '"""')
    call append(3,"Author:         Kai Xia <xiaket@gmail.com>")
    call append(4,"Filename:       " . expand("%"))
    call append(5,"Last modified:  2010-04-01 00:00")
    call append(6,"")
    call append(7,"Description:")
    call append(8,"")
    call append(9, '"""')
endf
function AddTitleSH()
    call setline(1, "#!/bin/sh")
    call append(1,"# ")
    call append(2,"# Author:         Kai Xia <xiaket@gmail.com>")
    call append(3,"# Filename:       " . expand("%"))
    call append(4,"# Last modified:  2010-04-01 00:00")
    call append(5,"# ")
    call append(6,"# Description:")
    call append(7,"# ")
endf
function UpdateDate()
    normal m'
    exe "1,7 s/Last modified:.*/Last modified:".strftime("  %Y-%m-%d %H:%M")."/e"
    normal ''
endf
autocmd bufnewfile *.py call AddTitlePython()
autocmd bufwritepre *.py call UpdateDate()
autocmd bufnewfile *.sh call AddTitleSH()
autocmd bufwritepre *.sh call UpdateDate()
</code></pre>

这个snippet大致的逻辑是对于py/sh这两个后缀的新文件, 我们自动增加一个脚本的header, 记录脚本的信息. 有这种snippet的好处在于我们能够有一个比较干净统一的脚本header, 而且能够自动更新这些脚本文件上次编辑的时间. 有兴趣的同学将上面这一段加到自己的.vimrc就可以试试效果了.

昨天周会时, 丹丹提出想修改一下这个snippet, 给没有加上header的文件自动加上header. 另外, 之前我对这个网上找来的snippet也有腹诽, 不能自动识别文件名是很让人讨厌的. 为此, 今天我就着手修改这个snippet. 但是看了看发现可修改性比较差, vim脚本的语法比较奇怪, 我也不太愿意为了实现这个功能再钻进去仔细看. 好在想到现在我们用的vim都支持python, 所以尝试用python来进行vim脚本编程.

关于vim的python脚本编程, 我主要参考了下面这些链接:

* [07年PyCon上的报告](http://www.tummy.com/presentations/vimpython-20070225/)
* [vim官方文档: The Python Interface to Vim](http://vimdoc.sourceforge.net/htmldoc/if_pyth.html)
* [某篇博客文章](http://orestis.gr/blog/2008/08/10/scripting-vim-with-python/)

要实现的功能大概包括:

* 新打开py/sh文件时, 自动加上header, 包括作者, 时间, 文件名.
* 打开已存在的py/sh文件时, 如果文件开头没有header, 则自动加上.
* 保存时自动更新header里面的修改时间和文件名.
* 如果我们不希望自动给这个文件加上header, 则删除header, 保存时不会自动写header.

于是大概试着写出了类似这样的add_header函数:

<pre class="code" data-lang="python"><code>
sh_header = """#!/bin/sh
#
# Author:         %(author)s
# Filename:       %(filename)s
# Last modified:  %(date)s
#
# Description:
#
"""

def add_header():
    import vim
    from datetime import datetime

    supported_suffix = ["py", "sh

    current_buffer = vim.current.buffer
    filename = current_buffer.name.split("/")[-1]
    suffix = filename.split(".")[-1]
    if suffix not in supported_suffix:
        return

    author = vim.eval("g:XY_HEADER_AUTHOR")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    header = current_buffer[:7]
    header_content = "\n".join(header)
    if not "Last modified" in header_content:
        suffix = filename.split(".")[-1]
        if suffix in ["py", "sh"]:
            str_tmplt = globals().get("%s_header" % suffix).rstrip()
            str_content = str_tmplt % {
                'author': author,
                'filename': filename,
                'date': date,
            }
            _range = current_buffer.range(0, 0)
            _range.append(str_content.split("\n"))
</code></pre>

代码逻辑挺简单, 对于py和sh后缀的文件, 创建一个range对象, 然后把我们的header填进去即可. 我另外试过直接修改current_buffer, 不过不管用. 前面这段代码是python相关的, 而vim那一段则是这么写的:

<pre class="code" data-lang="vim"><code>
let g:XY_HEADER_AUTHOR = "Kai Xia <xiaket@gmail.com>"
autocmd bufread,bufnewfile * python add_header()
autocmd bufwritepre * python update_header()
</code></pre>

为了方便修改, 所以我没有限制这儿buffer的文件类型. 而是在add_header函数里确定. 理论上我们可以把对文件类型的判断放在这儿, 但是我担心当文件类型比较多时这儿会比较乱, 还是放进python函数, 至少我读起来会舒服一点儿.

接下来是update_header函数, 这个函数编写相对较容易. 我本来想直接用python来进行字符串操作, 但后来觉得能重用已有的代码更是一种美德:

<pre class="code" data-lang="python"><code>
def update_header():
    import vim
    from datetime import datetime

    supported_suffix = ["py", "sh
    current_buffer = vim.current.buffer
    filename = current_buffer.name.split("/")[-1]
    suffix = filename.split(".")[-1]
    if suffix not in supported_suffix:
        return

    author = vim.eval("g:XY_HEADER_AUTHOR")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    vim.command("silent! 1,7 s/Filename.*/Filename:       %s/e" % filename)
    vim.command("silent! 1,7 s/Last modified:.*/Last modified:  %s/e" % date)
</code></pre>

相对于原来的snippet, 这儿最后的命令我用silent前置了下. 避免当文件行数少于7时vim的报错. 我本来还想用下vim模块的error这个异常, 但貌似即使我捕获了异常这个错误信息仍会显示在vim里. 干脆加上这个silent, 一了百了.

到这儿, 这个脚本的完成度已经比较高了, 但我在试用中又发现了一些问题. 包括即使我删掉了误增加的header, vim还是会写header. 我查了好久也没法确定为什么关闭文件时会调用bufread这个自动命令. 后来用比较恶心的办法搞定了: 我在进入buffer后检查是否存在某个变量, 如果变量存在则直接退出. 如果变量不存在, 则设置变量, 并添加header. 这样能够避免同一个buffer内对header的重复添加.

另一个恶心的地方在于, 我打开python标准库里的文件时, 我的插件会自动给标准库的文件加上header, 这无论如何不应该被接受. 为此, 我想过的解决方案包括:

1. 拿到被打开的文件的路径, 只有当这个路径里保护svn/subversion这种字样时才加header.
1. 检查目录的权限, 如果我没权限写, 不要加header.
1. 直接屏蔽掉某些目录, 例如某个目录是/usr开头, 则永远不写header.

目前采用了第三种方案, 不过或许我该把2也加进去.

最后放一段目前完成的代码, pygments对vim中的python脚本的支持还比较一般, 所以颜色可能会比较乱.<p>

<pre class="code" data-lang="vim"><code>
" python and shell script header.
let g:XY_HEADER_AUTHOR = "Kai Xia <xiaket@gmail.com>"
autocmd bufread,bufnewfile * python add_header()
autocmd bufwritepre * python update_header()

python << EOF
py_header = """#!/usr/bin/env python
#coding=utf-8\n\"\"\"
Author:         %(author)s
Filename:       %(filename)s
Last modified:  %(date)s

Description:


\"\"\"
"""

sh_header = """#!/bin/sh
#
# Author:         %(author)s
# Filename:       %(filename)s
# Last modified:  %(date)s
#
# Description:
#

"""

def should_do_write(filepath):
    """This function determines whether we should add header or
    update header for a file.
    """
    import os

    supported_suffix = ["py", "sh
    exclude_dir = ['usr', 'mnt', 'var', 'private']

    filename = filepath.split("/")[-1]
    suffix = filename.split(".")[-1]
    if suffix not in supported_suffix:
        return False

    if not os.path.exists(filepath):
        # file does not exist, so this is a new buffer, we shall check
        # whether we have write access to the directory.
        directory = os.path.split(filepath)[0]
        if not os.access(directory, os.W_OK):
            # If we do not have write access to the directory, we give up.
            return False
    else:
        # existing file, check whether we have write access to it.
        if not os.access(filepath, os.W_OK):
            # no permission, do nothing.
            return False

    file_dir = filepath.split('/')[1]
    if file_dir in exclude_dir:
        return False

    return True

def add_header():
    import vim
    from datetime import datetime

    current_buffer = vim.current.buffer
    filename = current_buffer.name.split("/")[-1]
    if not should_do_write(current_buffer.name):
        return

    on_enter = vim.eval("exists('b:ENTERED')")
    if on_enter == '0':
        vim.command("let b:ENTERED = '1'")
    else:
        # variable exist, this function has been run on this buffer, so quit.
        return

    author = vim.eval("g:XY_HEADER_AUTHOR")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    header = current_buffer[:7]
    header_content = "\n".join(header)
    if not "Last modified" in header_content:
        suffix = filename.split(".")[-1]
        if suffix in ["py", "sh"]:
            str_tmplt = globals().get("%s_header" % suffix).rstrip()
            str_content = str_tmplt % {
                'author': author,
                'filename': filename,
                'date': date,
            }
            _range = current_buffer.range(0, 0)
            _range.append(str_content.split("\n"))

def update_header():
    import vim
    from datetime import datetime

    current_buffer = vim.current.buffer
    filename = current_buffer.name.split("/")[-1]
    if not should_do_write(current_buffer.name):
        return

    author = vim.eval("g:XY_HEADER_AUTHOR")
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    row, column = vim.current.window.cursor
    vim.command("silent! 1,7 s/Filename.*/Filename:       %s/e" % filename)
    vim.command("silent! 1,7 s/Last modified:.*/Last modified:  %s/e" % date)
    vim.current.window.cursor = (row, column)
EOF
</code></pre>
