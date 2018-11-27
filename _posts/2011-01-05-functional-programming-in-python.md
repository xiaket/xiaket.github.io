---
title:  "玩玩Python中的函数式编程"
date:   2011-01-05 22:22 +0800
ref:    functional-programming-in-python
---

最近又开始重做[Project Euler](http://projecteuler.net/)的题目, 之前只要求做出结果来, 离保证每道题都能在五分钟内算完的要求还差得挺远. 自己看过Pro Python也蠢蠢欲动, 想练习一下看到的技巧们.

今天手头上玩的是[第21题](http://projecteuler.net/index.php?section=problems&id=21), 题目不难, 我玩这一题很长时间是想用尽量短的方法写一个求一个合数的因数的和的办法. 题目链接中给了例子, 220这个数有1, 2, 4, 5, 10, 11, 20, 22, 44, 55和110这11个因数, 其和是284. 我想做的就是写一个尽量短的函数来求得这个数.

首先, 脏活累活就不要自己做了, 质因数分解这种事情还是交给库函数吧:

<pre class="code" data-lang="python"><code>
from sympy import factorint

print factorint(220)
# {2: 2, 11: 1, 5: 1}
</code></pre>

`sympy`这个库有需要的同学自己去装吧, 这儿不进一步讨论了. `factorint`这个函数返回一个字典, 键是质因数, 值是质因数的指数. 此处, `(2**2)*(5**1)*(11**1) = 220`. 我们要做的事情就是尽量高效地利用这个字典算得我们要求的`[1, 2, 4, 5, 10, 11, 20, 22, 44, 55, 110]`这个列表.

首先需要放弃的思路是对每一个质因数写一个for来循环, 因为我们没办法判断质因数到底有多少个. 我们接下来考虑的方式是列表的乘法, 类似:

<pre class="code"><code>
[1, 2, 4] * [1, 5] = [1, 2, 4] + [5, 10, 20] = [1, 2, 4, 5, 10, 20]
</code></pre>

对每个质因数都重复这个过程, 就能得到所求的列表:

<pre class="code" data-lang="python"><code>
from sympy import factorint

prime_dict = factorint(220)

factors = [1]
for key in prime_dict:
    this_prime = []
    for i in xrange(prime_dict[key]+1):
        this_prime.append(key**i)
    _list = []
    for number in this_prime:
        for factor in factors:
            _list.append(number*factor)
    factors = _list

factors = factors[:-1]
</code></pre>

这段代码不算太复杂, 首先就是拿到字典, 对于每个字典里的质数, 我们拿一个空列表来装类似`[1, 5]`这样的列表, 这个列表在后面和之前已有的列表相乘, 乘出来的结果放在`_list`这个临时列表里面, 然后将这个临时列表的内容丢给`factors`这个列表. 循环完了之后, 我们就拿到了220这个数的所有因数的列表, 由于220本身也被包含在这个列表里了, 所以我们要把这个数去掉.

这段代码能做事了, 不过还不够酷. 我们来压缩下, 首先在各个地方使用下列表解析, 这样, 主循环体变为:

<pre class="code" data-lang="python"><code>
factors = [1]
for key in prime_dict:
    this_prime = [key**i for i in xrange(prime_dict[key]+1)]
    _list = [number*factor for number in this_prime for factor in factors]
    factors = _list
</code></pre>

而显然我们还可以再用一次列表解析把这两句话合起来:

<pre class="code" data-lang="python"><code>
factors = [1]
for key in prime_dict:
    _list = [number*factor for factor in factors for number in [key**i for i in xrange(prime_dict[key]+1)]]
factors = _list
</code></pre>

由于列表解析的特性, `_list`这个临时列表是自动生成的:

<pre class="code" data-lang="python"><code>
factors = [1]
for key in prime_dict:
    factors = [number*factor for factor in factors for number in [key**i for i in xrange(prime_dict[key]+1)]]
</code></pre>

到此, 我们已经可以写出一个很短的函数了:

<pre class="code" data-lang="python"><code>
def factor_sum(num):
    factors = [1]
    prime_dict = factorint(num)
    for key in prime_dict:
        factors = [number*factor for factor in factors for number in [key**i for i in xrange(prime_dict[key]+1)]]
    return sum(factors) - num
</code></pre>

除掉一些overhead, 基本的操作是在三行内完成的. 不过这个还不够让人满意, 因为中间列表乘来乘去的步骤应该可以更简单一点. 我们可以注意到对于`prime_dict`的处理我们是一层一层地用的, 因此我们可以试着使用`reduce`函数来简化我们的函数. 由于`reduce`里面的函数要接受两个参数, 因此我们不能将`prime_dict`的属性直接丢给`reduce`函数, 而是在后面部分给出列表的列表更合理. 列表的列表是用下面的函数给出的:

<pre class="code" data-lang="python"><code>
[[key**i for i in xrange(prime_dict[key]+1)] for key in prime_dict]
</code></pre>

这段代码里面里面一个方括号用来生成里面一层列表, 对于220, 这个表达式给出的结果为:

<pre class="code"><code>
[[1, 2, 4], [1, 11], [1, 5]]
</code></pre>

然后我们就可以放心地使用reduce函数了:

<pre class="code" data-lang="python"><code>
reduce(lambda x, y: [a*b for a in x for b in y], [[k**i for i in xrange(prime_dict[k]+1)] for k in prime_dict])
</code></pre>

这段代码中定义了一个匿名函数, 这个函数的逻辑很简单, 就是对于拿到的两个参数(两个都是列表), 循环然后利用其乘积生成一个列表. 上面这句代码的运行结果为:

<pre class="code"><code>
[1, 5, 11, 55, 2, 10, 22, 110, 4, 20, 44, 220]
</code></pre>

然后和前面一样, 写成一个正统的函数:

<pre class="code" data-lang="python"><code>
def factor_sum(num):
    prime_dict = factorint(num)
    if len(prime_dict) == 1:
        return [(k**v-1)/(k-1) for (k, v) in prime_dict.iteritems()][0]
    else:
        return sum(reduce(lambda x, y: [a*b for a in x for b in y], [[k**i for i in xrange(prime_dict[k]+1)] for k in prime_dict])) - num
</code></pre>

注: 原来写到这儿, 没做更细致的推算, 导致当prime_dict只有一个元素时, 没有办法进行reduce, 因此需要用等比数列求和公式来算. 前面那个函数没有这个问题(因为没用`reduce`).

到这儿, 我已经比较满意了, 主要的逻辑都是在一句话里面写完的. 当然不得不说, 在正式项目里面我肯定不会这样去写代码, 因为可读性差, 而且效率不一定高(很有可能会更糟糕), 另外, 这一行也太长了...
