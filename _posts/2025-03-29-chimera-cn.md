---
title:  Chimera Linux折腾记
date:   2025-03-29 17:16
ref:    chimera-linux-cn
---

这篇文章记录一下自己是如何在一台十年前的MacBook Air上折腾[Chimera Linux](https://chimera-linux.org/)的.

先说一下为什么, 主要是我自己用过的发行版虽然很多, 但是都有了很多很多的历史包袱. 我想看看现代一点的发行版能够做到什么程度. 从介绍来看, Chimera Linux的技术路线比较讨喜. 比如没有使用systemd, 比如使用了FreeBSD里面的userland.

具体的折腾算是一波三折. 首先比较顺利地下载镜像刷到U盘然后在这台MacBook Air上U盘启动进系统一气呵成, 让人感觉有点不现实. 不过再仔细一看, 发现硬盘没成功加载, 蓝牙虽然能用但是无线网卡却没识别. 不算太圆满的开局, 不过还能接受, 至少比我之前折腾FreeBSD要顺利得多了.

然后开始解决硬盘的问题, 拿着报错查了下, 发现是一个内核参数的问题, 需要在内核启动时加上`intel_iommu=off`, 不算什么特别的, 需要重启电脑而已, 而且每次进系统之前都要记得去grub里面改, 否则硬盘就不能识别. 正确的修改方式是编辑`/etc/default/grub`, 不过对于LiveCD, 这种做法是无效的.

然后就是更纠结的无线网卡的问题. 症状是`/dev/net`下面没设备文件. `lspci`看了下, 是BCM4360, LiveCD中默认加载的`b43`和`bcma`模块都没法带动这个卡. 查到一些文档, 比如[这个](https://github.com/antoineco/broadcom-wl), 于是要编译内核模块了. 本想在Live CD环境中编译, 这样unknown会少很多, 不过repository里面的内核版本和Live CD里的内核版本有区别, 于是我就打算先安装系统, 然后再去解决驱动的问题.

我按照[官方文档](https://chimera-linux.org/docs/installation)分好了区(ZFS+EFI+boot), 挂载, 然后执行`chimera-bootstrap -l /media/root`来将LiveCD中的内容复制到新分区中去. 这一步最后会有报错, 记得好像是说无法跨设备来创建硬链接. 我猜是这个脚本/命令没有处理好这种细节, 于是就忽略了. 后面开始执行`apk upgrade --available`时速度很慢, 因为网络走的是手机热点通过蓝牙来传递数据, 所以带宽很小. 我升级了一群包后直接Ctrl-C了, 后面正常安装grub后重启没问题, 但是进不了X, 这个时候蓝牙服务也没打开. 这个比较麻烦, 因为之前从来没有处理过命令行下没网络修蓝牙的情况, 而且即使蓝牙修好了还需要通过蓝牙连接到手机才能上网. 于是重启, 再次祭出LiveCD后挂载zfs进去修了. 记得不错的话, 要么是`sddm`没安装, 要么是`sddm-dinit`没安装, 安装后就都能正常工作了.

当然当然还要继续编译网卡驱动呢. 参考了[这个SlackBuild](https://slackbuilds.org/repository/15.0/network/broadcom-wl/), 把[这个脚本](https://slackbuilds.org/slackbuilds/15.0/network/broadcom-wl/broadcom-wl.SlackBuild)稍稍改了下([gist]()), 就能正常编译了.

当然现实中才没这么简单呢, 先要装`clang`和`gmake`, 然后要去装/更新`linux-stable{,dev}`, 最坑的是还要安装`wireless-regdb`这个包. 原始脚本中应该是使用gcc来编译的, 而Chimera Linux是clang. 我懒得去找环境变量, 直接将clang软链接成了gcc, 编译也没啥问题. 编译成功后可以得到`wl.ko`这个内核模块文件, 用`modprobe`就能正常加载, 不管是`modprobe -r`还是加黑名单, 都能让这个网卡用我们刚编译的`wl.ko`来启动(PCI信息里也能看到), 但是我的`/dev/net`里仍是只有一个手机共享热点的`tun`设备. 最后是死马当活马医似的将`dmesg`的报错(加载`regulatory.db`出错)查了下, 发现真是缺少数据库的缘故. apk安装对应的这个软件包后就好了.

最后加上一点小杂感:

* Userland里面的代码并没有让Chimera Linux能够stand out. 这个userland中的软件包其实很少, 对用户的影响也很subtle.
* cports的组织形式不错, 很有些现代版ports的感觉. 目前里面的包数量还比较有限, 希望后面发展会更好.
* 现在的Chimera Linux还不算太成熟. 一方面, LiveCD安装好后, 不应该出现缺少wireless-regdb/sddm-dinit这样的问题. 另外一方面, 不少东西得自己折腾(比如中文输入法就得自己从源码编译, 软件仓库和cports里都没有).

我自己会继续跟进这个发行版, 目前来看还是有一定潜力的, 作者的更新也很勤快.