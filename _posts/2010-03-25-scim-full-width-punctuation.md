---
title:  "重新编译scim解决半角标点的问题"
date:   2010-03-25 13:12 +0800
ref:    scim-full-width-punctuation
---


现在我的Slackware上拼音输入法用的是scim, 虽然词库比ibus差些, 但是稳定性还是好不少的. 不过scim-pinyin的全角/半角字符的问题一直让我很纠结. 我习惯了在中文状态下使用英文标点. 但是scim默认打开的时候使用的是全角的中文标点. 为了解决这个问题, 研究了一早上, 通过重新编译scim-pinyin搞定 了这个问题.

scim的设置界面(scim-setup)里肯定是没有这个选项的了. 而scim的配置文件`~/.scim/config`是由这个设置界面生成的. 于是, 我们首先要确定有没有什么隐藏的配置选项. 为此, 从sf上拿到scim-pinyin的最新版本`scim-pinyin-0.5.91`, 解包, 研究了下源码, 发现可能的配置选项都是在`src/scim_pinyin_imengine_config_keys.h`文件里. 这个用一下grep, 关键字选择`~/.scim/config`里的相关字符串, 很容易找到. 首先整理下这个里面有的配置项, 再和我的配置文件里已有的配置项比较了下, 发现没有我所需要的选项. 看来必须要重新编译scim-pinyin了.

至于重编scim-pinyin能解决问题, 也是看到了[linuxsir上的一个帖子](http://www.linuxsir.org/bbs/thread89948.html), 里面说得很详细, 连代码的行数都给出来了. 无论如何, 试试吧. SA天生就是折腾的命. 其实这个过程也不算繁复, 不过我的slackware上编译环境有些non-conventional, 所以费了点时间.

首先拿到scim-pinyin的源码包, 解包, 直接去找前面那个帖子所说的文件. 果然, 这段代码还没变. 按照帖子里的说法进行修改, 接下来删除原来那个压缩包, 自己再将改过的代码打包一次, 搞定.

偶们接下来就该编译了. 去[slackbuilds.org](http://www.slackbuilds.org)上找scim-pinyin的slackbuild文件, 没找到. 无奈, 尝试了下src2pkg, 貌似有点问题. 哎哎, 还是找个.Slackbuild文件来比较靠谱. 这个也不算太难找, Google了下, 发现[这个地方](http://slackware.osuosl.org/slackware_source/x/scim-pinyin/)有, 下载拿到. 接下来编译. 结果发现两类错误, 第一类是报找不到.h文件, 这个由于没有正确设置-I参数而引起的. 我本希望修改.Slackbuild文件, 添加了一个-I能够解决这个问题, 后来发现编译时命令行里的-I仍然没有使用我指定的参数, 懒得管了, 做了几个软链接丢到了/usr/include, 这样就没问题了:

<pre class="code" data-lang="bash"><code>
[root@slk:/usr/include]ln -s /usr/src/linux/include/linux .
[root@slk:/usr/include]ln -s /usr/src/linux/arch/x86/include/asm .
[root@slk:/usr/include]ln -s /usr/src/linux/include/asm-generic .
</code></pre>

第二个问题是报strlen这样的函数没有被定义, Google了下, [前人给出了解决方案](http://blog.csdn.net/sanlinux/archive/2010/01/10/5171234.aspx). 为啥又需要修改源代码呢? 哎, 再次把刚才打好的包解开, 按照这个方案里的提示进行了修改. 修改的时候还发现了一个作者的笔误, 在scim_special_table.cpp里, 他将"#define Uses_C_STRING"写成了"#define Uscs_C_STRING". 嗯, 莎翁说得好, To err is human.

搞定了这两个问题, 编译成功, 打包, 用installpkg安装, 重启scim, 搞定~~
