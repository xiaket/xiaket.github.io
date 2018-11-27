---
title:  "Django中的两个命令行输出添加ASCII颜色的函数"
date:   2010-01-03 00:09 +0800
ref:    python-ascii-color-functions
---

代码在`django/utils/termcolors.py`中, 相关应用的例子在下面:

<pre class="code" data-lang="python"><code>
colorize('hello', fg='red', bg='blue', opts=('blink',))
print colorize('first line', fg='red', opts=('noreset',))
print 'this should be red too'
print colorize('and so should this')
print 'this should not be red'
</code></pre>

支持常见的ASCII效果:

<pre class="code"><code>
'bold'
'underscore'
'blink'
'reverse'
'conceal'
'noreset'
</code></pre>

这个文件里面的另一个make_style函数更赞~

<pre class="code" data-lang="python"><code>
def make_style(opts=(), **kwargs):
"""
    Returns a function with default parameters for colorize()

    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print bold_red('hello')
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
return lambda text: colorize(text, opts, **kwargs)
</code></pre>

这两个东东原理都很简单, 代码也是很易懂, 不再多解释了~ 以后项目中有需要直接输出彩色文字的需求直接调用这两个函数就行了~
