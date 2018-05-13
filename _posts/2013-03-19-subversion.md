---
title:  "svn避免跟踪某些目录"
date:   2013-03-19 11:59 +0800
lang: zh
---

偶们组的代码都在同一个svn库里面, 大家一起协作编辑. 但是作为普通一员, 有时候也不太会关心其他项目的svn提交情况. 为避免每次在主目录里svn up时收取到其他项目目录的更新, 我之前的做法是只co某几个我关心的目录而不是co主目录. 但这毕竟算不上是解决这个问题的正道, 而且新增加的目录自己就没有跟踪. 最近换用Homebrew, 升级了本机的svn, 顺便解决了下这个小问题.

首先是我的svn提示我做svn upgrade, 这个操作的目的是把本地的旧svn管理方式升级到新的方式. 最直接的区别是每个svn子目录下不再有一个碍眼的.svn目录. svn upgrade后svn up, 保证本地的代码库是最新的.

然后要在主目录下执行下面的命令来实现我们刚才所说的需求:

```sh
svn update --set-depth=exclude dir1 dir2 dir3
```

这儿dir1/dir2/dir3是你不期望跟踪的子目录的名字. 执行完这个操作后, 会有类似下面的输出:

```sh
[xiaket@rondo:~/.Repos/projects]svn update --set-depth=exclude dir1 dir2 dir3
D    dir1
D    dir2
D    dir3
```

淡定, svn up是不会影响到主干的. 这儿的D是本地的标注而已. 而且, 如果这个目录存在, svn会删除这个目录.

如果你还需要在某个子目录下取消跟踪某些孙目录的跟踪, 进入这个子目录, 重复执行上面的命令即可. 另外, 如果你哪天改变主意了, 认为dir3这个目录值得自己跟踪一下进展, 可以执行下面的命令:

```sh
svn update --set-depth=infinity dir3
```

最后唠叨一句, 上面所有这些内容都不需要服务器的支持. 你可以放心大胆地升级本地的subversion, 而不用理会你的svn服务器的版本.
