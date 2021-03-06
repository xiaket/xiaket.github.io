---
title:  "翻译: scp协议原理"
date:   2010-05-18 12:21 +0800
ref:    how-scp-protocol-works
---

译自: [http://blogs.sun.com/janp/entry/how_the_scp_protocol_works] (http://blogs.sun.com/janp/entry/how_the_scp_protocol_works). 原作者为[Jan Pechanec](http://blogs.sun.com/janp/). 这篇文章主要讲solaris中的scp协议实现. 本人对原文做了适当的润色, 希望能更易理解而不易产生误会. 水平有限, 有错误请不吝指出.

### rcp协议简史

rcp命令1982年第一次出现在4.2版的BSD里面([man页面链接](http://blogs.sun.com/janp/resource/scp/rcp.txt)). 近30年的岁月让这个命令有了一些变化, 所以最初的rcp和现代的rcp会有些不一致的地方. rcp的基本协议在ssh-1.2.x版本里有实现, 而ssh-1.2.x又是OpenSSH的基础. 由于Solaris用的SSH工具(SunSSH)是OpenSSH的分支, 因此前面所讲的rcp协议到现在都还是在起作用. 说了这么多, 我也许应该把这篇文章的标题改成`rcp协议原理`, 不过这样看起来就不够酷了, 你懂的.(译者注: 这样偶就看不到这篇文章了...)

### 协议工作方式

前面已经说过, rcp和scp在协议层面上没有区别, 不同在于传输时使用了rlogin. 从现在开始, 我就只讲scp了. 其使用摘要如下:

<pre class="code" data-lang="bash"><code>
scp [options] [user@]host1:]file1 []... [ [user@]host2:]file2
</code></pre>

除开远程服务器之间的文件复制这个特殊情况, scp会先解析命令行参数, 然后打开一个到远程服务器的连接. 再通过这个连接起另一个scp进程, 这个进程的运行方式可以是源模式(source)也可以是宿模式(sink). (译者注: 前者是数据提供者, 源头, 以源模式运行的scp进程后面会被称作是源端. 后者是数据的目的地, 归宿, 以宿模式运行的scp进程后面会被称作是宿端)前者读取文件并通过SSH连接发送到另一端, 后者通过SSH连接接收文件. 源模式和宿模式是通过-f (from)和 -t (to)这两个隐藏选项来启动的. 这两个参数仅供命令内部使用, 因此没写进文档. (译者注: 你执行scp -t不会给出非法参数的报错提示, 而scp -s就会, 因为没有-s这个选项.) 除了这两个隐藏参数外, 还有另一个隐藏参数-d, 表示复制的对象是一个目录而不是文件.

下图给出了一个简化后的scp源/宿模式工作示意图:

<pre class="code" data-lang="bash"><code>
+-----------+   remote command: scp -t file2    +------+
| ssh hostB |---------------------------------->| sshd |
+-----------+                                   +---+--+
     ^                                              |
     |                                              |
     |fork()                                  fork()|
     |                                              |
+----+-----------------+                +-----------V--+
| scp file hostB:file2 |                | scp -t file2 |
+----------------------+                +--------------+
</code></pre>

### 协议

下面介绍传输协议是如何工作的. 你不如先暂时忘了ssh, sshd以及两台机器之间的连接这些东东. 如果我们只关注以源宿两种模式工作的scp命令的话, 上图可以简化成:

<pre class="code" data-lang="bash"><code>
data transfer
+------------------+   ___________   +--------------+
| scp fileX hostY: | ->___________-> | scp -t fileX |
+--------.---------+                 +-------.------+
         |                                   |
         |read()                             |write()
   __....|....__                       __....|....__
   =__  fileX  __:'                    =__  fileX  __:'
     `''''''''                           `''''''''
</code></pre>

需要注意的是, 永远不会有两个工作模式一样的scp协同工作. (译者注: 你可以想象下两个源端互相期待对方给自己传文件会是啥情况...) 远程服务器上的scp进程选定一种模式后, 本地的scp进程(就是本地用户命令行起的这个进程)会自动选定另一种模式, 因为这个本地进程会于用户交互.

#### 源端

协议信息是由文本和二进制数据混合构成的. 例如, 当我们要传出一个普通文件时, 协议消息的类型, 文件的权限位, 长度及文件名都会以文本的方式发送, 接着在一个换行符后发送文件的内容. 我们在后面会更详细地讨论这一点. 协议消息内容可能类似:

<pre class="code"><code>
C0644 299 group
</code></pre>

二进制数据传输前需要传输的文本信息可能更多. 源端会一直等宿端的回应, 直到等到回应才会传输下一条协议文本. 在送出最后一条协议文本后, 源端会传出一个大小为零的字符'\0'来表示真正文件传输的开始. 当文件接收完成后, 宿端会给源端发送一个'\0'.

#### 宿端

来自源端的每条消息和每个传输完毕的文件都需要宿端的确认和响应. 宿端会返回三种确认消息: 0(正常), 1(警告)或2(严重错误, 将中断连接). 消息1和2可以跟一个字符串和一个换行符, 这个字符串将显示在scp的源端. 无论这个字符串是否为空, 换行符都是不可缺少的.

### 协议消息类型列表

* `Cmmmm <length> <filename></filename></length>`表示传输单个文件, mmmm是文件的权限位. 实例: C0644 299 group

* `Dmmmm <length> <dirname></dirname></length>`表示开始整个目录的递归复制. 此处文件长度将会忽略, 但是不可缺少. 实例: `D0755 0 docs`

* `E`表示目录的结束(D-E这一对可以嵌套使用, 这也是我们能正常递归复制目录树的原因.)

* `T<mtime> 0 <atime> 0</atime></mtime>`. 当命令行给出-p选项时, 这一类协议消息用来传输所传递的文件的修改时间和访问时间(我猜你应该知道为啥我们不把文件创建时间传到宿端吧?). 时间记录了从UTC 1970.01.01 00:00:00到现在所经历的秒数. 这一类协议消息在最初的rcp实现中并未出现. 实例: `T1183828267 0 1183828267 0`

传完了这些消息后就开始传文件数据了. 宿端从数据流中读取之前协议消息中指定的文件长度. D和T需要在其他消息之前指定. 这是因为如果这两类消息放在其他消息之后, 这两类消息的内容具体是消息还是数据就不清楚了. 我们可以总结如下:

* 传完了C类消息后开始传输文件数据.
* 在传完了D类消息后, 要么出现C类消息, 要么出现E类消息.

### 最大文件大小和文件完整性

scp所能传输的最大文件大小是由scp协议, scp软件, 操作系统以及文件系统综合决定的. 由于OpenSSH用long long int来放文件大小, 因此理论上可以传输的最大文件大小是2^63 Byte. 给一个参考值, 2^40 Byte的大小是1T. 这意味着我们可以认为协议本身没有文件大小的限制.

scp本身不提供对文件完整性的保护, 这一特性是在ssh协议那一层完成的. 你可以参考[我之前写的博客文章](http://blogs.sun.com/janp/entry/ssh_messages_code_bad_packet), 也可以直接去围观[RFC43253](http://www.ietf.org/rfc/rfc4253.txt).

### 例子

讲协议是扯不清楚的, 直接看例子更直观更形象.

#### 1. 本地文件复制到另一位置

<pre class="code" data-lang="bash"><code>
$ rm -f /tmp/test
$ { echo C0644 6 test; printf "hello\\n"; } | scp -t /tmp
test                 100% |***************************| 6       00:00
$ cat /tmp/test
hello
</code></pre>

好玩吧? 我用了printf命令, 这样我们能够很清楚地看见为什么文件长度为6. 接下来我们试试复制一个目录.

#### 2. 本地目录复制到另一位置

我们准备将一个名为testdir的目录, 内含一个名为test的文件, 递归地复制到/tmp下去.

<pre class="code" data-lang="bash"><code>
$ rm -rf /tmp/testdir
$ { echo D0755 0 testdir; echo C0644 6 test;
printf "hellon"; echo E; } | scp -rt /tmp
test                 100% |****************************| 6       00:00
$ cat /tmp/testdir/test
hello
</code></pre>

请注意, 我们在此处用了`-r`参数, 因为我们要复制整个目录.

#### 3. 将另一位置的目录复制到本地

之前的例子中, 管道里的scp都是充当宿端. 这个例子里面, scp进程的角色是源端. 就像前面说的那样, 我们必须要对每个成功的消息和文件传输加以应答. 另外, 这个例子只是模拟应答的过程, 而没有真正去创建文件和文件夹. 因为要创建的东西都已经在你的终端里打印出来了.

<pre class="code" data-lang="bash"><code>
$ cd /tmp
$ rm -rf testdir
$ mkdir testdir
$ echo hello &gt; testdir/test
$ printf '\000\000\000\000\000\000' | scp -qprf testdir
T1183832947 0 1183833773 0
D0700 0 testdir
T1183833773 0 1183833762 0
C0600 6 test
hello
E
</code></pre>

解释下, 这次没有进度条了, 这是因为我们用了`-q`选项. 你可以看到传输了文件时间信息, 这是因为我们是用了`-p`选项. 另外, `-f`表示这一次scp进程是源端. 你可以发现我们丢了六个`\000`给scp, 这是我们模拟的传输过程中的应答. 第一个来开始传输过程, 四个响应消息, 一个响应文件传输结束. 对了吗? 不对, 我们还没响应最后的E呢. 此时看看退出状态:

<pre class="code" data-lang="bash"><code>
$ echo $?
1
</code></pre>

如果我们用七个`\000`, 就不会有问题了:

<pre class="code" data-lang="bash"><code>
$ printf '\000\000\000\000\000\000\000' | scp -qprf testdir
T1183832947 0 1183833956 0
D0700 0 testdir
T1183833773 0 1183833956 0
C0600 6 test
hello
E
$ echo $?
0
</code></pre>

#### 4. 发送错误消息

下面这个例子中, 我们将会返回2给scp, 你可以看到即使我们在这个2后面又发送了几个`\000`, scp命令也不接受后面的这些确认信息了.

<pre class="code" data-lang="bash"><code>
$ printf '\000\000\002n\000\000' | scp -qprf testdir

T1183895689 0 1183899084 0
D0700 0 testdir
</code></pre>

### 远程服务器shell配置文件有输出

有时候, 会有scp不能正常工作而ssh却一切正常的情况发生. 这通常是由于远程服务器的配置文件里有`echo/printf`而造成的. 下面展示几个例子:

#### 输入密码后, scp就卡住不动了

要重现这一症状, 在远程服务器的配置文件里面添加一行:

<pre class="code" data-lang="bash"><code>
echo ""
</code></pre>

为什么会有这种情况发生呢? 这是因为在源端的scp进程会等待第一个协议消息的确认信息. 如果拿到的不是0, 它会认为这是远程服务器错误提示的一部分, 并会接着无限期地等待标志消息结束的换行符. 由于你在第一个换行符后没有打印新的内容, 你本地的scp就卡住不动了. 一直处于read状态. 另一方面, 远程服务器在处理完配置文件后, 以宿端scp进程也就开始了它也会卡在read状态, 等待一个0来表示文件传输的开始. 好吧, 现在两边的scp都卡住不动了. 总结下, 这种情况下, 问题的起因是远程服务器的shell配置文件的输出参与了scp协议的对话.

#### 如果我将文件复制到远程服务器, scp执行完我的shell配置就退出了

这句话的意思是, scp只是将用户的shell配置文件打印出来的第一句话打印出来就退出了. 要重现这个问题, 可以执行下面的操作:

译者注: 这个实验会清空你的`.bashrc`... 慎用.

<pre class="code" data-lang="bash"><code>
$ echo 'echo "hi there!"' >> .bashrc
</code></pre>

然后执行scp命令:

<pre class="code" data-lang="bash"><code>
$ scp /etc/passwd localhost:/tmp
hi there!
$ echo $?
1
</code></pre>

这个问题和第一个问题很类似. 由于接收到的第一个字符不是0(这个例子中是'h'), 它会认为有问题, 一直读到下一个换行符. 将读到的东西打印出来, 然后退出.

这一类问题都比较容易解决, 用下面的命令, 当你真正是通过终端登录时才把你想要的东西打印出来即可.

<pre class="code" data-lang="bash"><code>
tty -s && echo "hi there!"
</code></pre>

#### 屏幕提示"协议错误: 未预料的<换行符>"然后scp退出了

同样和第一个问题类似, 但是你是从远程将文件复制到本地时会出现这种情况. 为什么呢? 你本地的scp是宿端, 等待源端传来的协议消息. 但是, 它拿到的是一个空行, 紧接着又拿到一个换行符. 这显然是违背协议的, 因此你本地的scp就退出了. 如果你在远程服务器配置文件里面还打印了额外的东西, 这些就会被当作是错误提示(除非这条消息是由一个有效的消息头标识符所引导的, 而如果这种纠结的事情真的发生了, 那么打印出来的错误提示会更难懂.) , 直到下一个换行符之前的输出都会被认为是错误提示的内容. 打印完这些内容后, scp就退出了. 例如我将下面这行加到我的shell配置里去:

<pre class="code" data-lang="bash"><code>
printf "XXXX"
</code></pre>

(printf不会自动打印换行符的, 记得吧?)第一条协议消息之前的所有输出都会被认为是错误提示:

<pre class="code" data-lang="bash"><code>
$ scp localhost:/etc/passwd .
Password:
XXXXC0644 1135 passwd
$ echo $?
1
</code></pre>

另外, 如果你恰好很纠结地在你的配置文件中指定了输出D之类的有效字符, 你拿到的消息就更纠结了.

<pre class="code" data-lang="bash"><code>
$ scp localhost:/etc/passwd .
Password:
protocol error: bad mode
$ echo $?
1
</code></pre>

知道教训了吧? 记得检查scp的退出状态!

### 协议的扩展性

rcp协议很简单, 我们现在想研究下它的可拓展性. 例如, 我们怎么样才能传输文件的ACL信息? 问题在于, 如何拓展这个协议, 让其具有向后的兼容性. 也许这个地方有些很简单的办法但是我没想到的, 不过我很怀疑这一点. 现在的问题是, 你不能拓展已有的消息. 比如, 看看我们往T消息结尾处添加一个字符串"123"会怎么样:

<pre class="code" data-lang="bash"><code>
$ { echo T1183832947 0 1183833773 0 123;
echo D0755 0 testdir; echo E; } | scp -rt /tmp
scp: protocol error: atime.usec not delimited
</code></pre>

C类消息也是一样:

<pre class="code" data-lang="bash"><code>
$ { echo D0755 0 testdir; echo C0644 6 test 123;
printf "hellon"; echo E; } | scp -rqt /tmp
$ ls -1 /tmp/testdir/
test 123
</code></pre>

而且你又不能添加一类新消息, 因为scp命令不能识别:

<pre class="code" data-lang="bash"><code>
$ { echo X 1 a; echo D0755 0 testdir; echo C0644 6 test;
printf "hellon"; echo E; } | scp -rt /tmp
scp: X 1 a
$ echo $?
1
</code></pre>

可能的办法:(有其他的办法咩?) 一个比较明显能解决问题的办法是给scp命令添加一个选项, 指明可以是用一些拓展协议消息. 如果运行失败的话可能远程服务器上的scp版本和本地的scp版本不一样, 然后就可以退到普通模式下运行了. 不过我不确定是不是真要搞得这么纠结. 有些scp软件的开发者已经在用sftp协议传输文件了, 而这也是我们想要做的事情. 我想也许可能在非交互方式下执行exec sftp, 再转换下参数就可以了.

### 远程服务器之间的复制

一个通常会问到的问题是, 为啥远程服务器之间的复制不能有密码输入之类的认证方式. 这不是bug, 这是特性. 代码上虽然可以实现有密码输入的认证, 但是由于实现的机理是建立hostA和hostB之间的直接连接, 而有人不希望把他在hostB的密码暴露给hostA, 所以代码上没有实现这一点. 远程服务器之间的文件复制是由本地的scp命令建立一个到hostA的连接, 然后执行"scp fileX hostB:..."来实现的.

我们最近更新了scp的手册页, 添加了这样一段:

<cite>
一般来说, 通过密码或键盘交互来用scp实现远程服务器之间的文件传输不能正常工作. 而用公钥, 基于主机或者GSSAPI的认证则是可行的. 对于公钥认证, 要么不能有非空的加密短语, 要么需要使用ssh认证转发功能. GSSAPI认证能够在kerberos_v5 GSS_API机制下使用, 但是必须启用GSSAPIDelegateCredentials选项.
</cite>

### 效率

现在你对scp的工作机理应该比较清楚了, 也应该比较容易理解为什么在一个延时比较高的网络环境下复制大量小文件会比将文件夹打包后传输需要长得多的时间. 每条协议信息以及传输结束后的确认信息的开销很大. 所以下一次, 你应该用类似下面的命令来传输大量小文件:

<pre class="code" data-lang="bash"><code>
tar cfv - testdir | ssh user@host 'cd /tmp; tar xfv -'
</code></pre>

### 结论

就这样吧, 总结下: rcp/scp协议是一个很简单的文件传输协议, 第一次在4.2BSD里面出现. 这个协议的可扩展性不强, 以后scp实现中可能会用sftp协议取代它.
