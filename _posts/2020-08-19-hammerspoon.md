---
title:  用Hammerspoon来代替Karabiner-Element和Magnet
date:   2020-08-19 14:24
ref:    hammerspoon
---

上个周末手贱升级了Big Sur Public Beta.

嗯, 和主题无关不是? 有关系, 升级后Karabiner-Element又不能用了, 这次仍是kernel extension出问题. 症状是程序启动一切正常, 所有熟悉的快捷键一律不能用. 上次由Karabiner升级到Karabiner-Element的折腾还历历在目, 现在这一幕又重演了. 于是愤而出走, 找来Hammerspoon. 不仅完全实现我在Karabiner-Element里面的需求, 而且还顺便把Magnet的需求也实现了, 这样menu bar的图标净减少一个, 可喜可贺.

说Hammerspoon之前, 先随便写几句Big Sur Public Beta:

1. 其实我真不是手贱而升级, 我有实实在在地需求的. 我想把[这个浏览器插件](https://github.com/tilfin/aws-extend-switch-roles)移植到Safari下来自己用. 而且我想搞一个folder structure出来, 因为我们的AWS账户已经太多太多了. 这个工作需要Xcode beta, 最好是在Big Sur下面跑(可能不需要, 不过谁知道呢). 顺便说一句, 这个也完成了, 代码可以在[这儿](https://github.com/xiaket/aws-extend-switch-roles-safari)找到.
2. 前面说了, 升级后Karabiner-Element不能跑了, 公司统一管理的杀毒软件也不能跑了(所以我昨天晚上回滚了). 这些都是因为kext的改动.
3. 升级后视觉元素有部分变化, 例如控制中心的改动我就很喜欢. 总体来说, 回到Catalina后感觉不太习惯, 觉得回到了上个时代.
4. 一个很恶心人的bug是视频音频播放有问题, 我没有找到复现的办法, 不过症状是音频播放没有任何声音, 视频播放没有任何图像. 这也是我愿意回滚的原因之一, 写代码的时候不能听歌实在不太对.
5. 另一个恶心人的bug是eventtap有时候不能正常工作, 所以有时重启后我用Hammerspoon定义的快捷键们能正常使用, 有时又完全不能使用.

接下来自然是说Hammerspoon. 我希望把我在Karabiner-Element和Magnet里面的配置糅合到一起, 定义一个全局的hyper键(右侧的⌘), 使得:

- hyper + S: 打开Safari
- hyper + K: 打开Kitty
- hyper + I: 锁屏
- hyper + P: 媒体播放/暂停
- hyper + 1: 当前应用窗口放到屏幕左上角
- hyper + 2: 当前应用窗口放到屏幕右上角
- hyper + 3: 当前应用窗口放到屏幕左下角
- hyper + 0: 当前应用窗口全屏
- hyper + .: 当前应用窗口放到当前屏幕右半边, 如果其已经在右半侧, 移到右边屏幕的左半侧.

所以, 一个是快捷键触发函数的需求, 一个是窗口管理的需求.

我上手的时候, 认为这应该是一个比较大路化的需求, Hammerspoon应该内置了这个特性, 试了以后才发现, Hammerspoon没有区分左右两边的⌘. 我用`hs.hotkey.bind`定义了hyper后, 左边和右边的cmd都能触发, 这可不行. 于是调研一番, 发现了有日本同学写了[hyperex](https://github.com/hetima/hammerspoon-hyperex). 拿过来试了下, 除了API不太满意以外, 功能方面一切正常. 后来说手贱也好说钻研也罢, 我把这个600多行的插件压到了80行, 重新实现了其中部分逻辑, 删除了我不需要的要素, 改名为[hiper](https://github.com/xiaket/etc/blob/master/hammerspoon/hiper.lua)后放进了我的etc repo里. 配置文件可以参考同目录下的[init.lua](https://github.com/xiaket/etc/blob/master/hammerspoon/init.lua).

先说下hyperex里面的让我不舒服的地方:

- hyperex支持将一个组合键映射到另一个组合键, 而我的需求只是将一个组合键映射到一个lua函数, 于是我砍掉了我不用的部分.
- 编码风格来说, 对于我这种看来比较trivial的需求, 完全没有必要用元类编程, 于是我干掉了所有的Impl类.

整个清理下来后, 整个实现的逻辑也更清晰了: 我定义两个eventtap(事件监听器), 一个监听`hs.eventtap.event.types.flagsChanged`, 即有modifier键被按下的事件, 一个监听`hs.eventtap.event.types.key{Down,Up}`, 用来处理正常的键入事件. 然后, 全程启动前一个监听器, 有事件的时候判断按下的按键是不是我们需要监听的按键. 如果不是的话直接忽略, 如果是的话, 打开另一个监听器, 看那个普通按键是什么, 如果是我们有定义过事件的按键, 则触发其对应的函数.

写`hiper.lua`花了我一两天, 写完感觉还是挺爽的. 于是周一晚上继续折腾了`magnet.lua`, 部分代码借鉴自[WinWin](http://www.hammerspoon.org/Spoons/WinWin.html), 自己只是完成了其中屏幕排序和窗口在屏幕间移动的逻辑. 整个文件写完100行出头, 但实际上工作量小很多(也是自己调试技巧在写完了`hiper.lua`后比较完善了).

这两个东西写完后总体感受是, lua是一门很干净的语言, 除了数组的index不是0让人错愕外, 写码的感受比写go还要爽.
