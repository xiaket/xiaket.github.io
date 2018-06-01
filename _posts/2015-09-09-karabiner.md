---
title:  "用Karabiner来自定义键盘快捷键"
date:   2015-09-09 09:51 +0800
lang: zh
ref:    karabiner
---

基于本人患有晚期强迫症的现实情况, 我用中文写作时所使用的标点必须是英文的. 为此, 我一直使用鼠须管. 这个输入法的词库比较硬伤, 而且使用上也有小问题, 比如我就不太敢升级它, 怕会弄坏东西. 昨天看了几篇网上的文章, 自己折腾了下, 除了解决了这个问题, 还引入了一些额外的功能.

本文所有的折腾都基于[Karabiner](https://pqrs.org/osx/karabiner/)和[seil](https://pqrs.org/osx/karabiner/seil.html.en).

首先要折腾的是中文输入法. 网上有篇文章解决了这个问题, 方法是对于中文输入法, 每次输入标点的时候, 首先按下大写锁定, 然后按下标点(这个时候标点就是英文的了), 最好再按下大写锁定, 取消大写. 这个办法略投机取巧, 不过还能接受. 具体配置方法是改Karabiner的`private.xml`. 我基本就是将那篇文章里提供的xml拿过来, 不过自己做了一些修改. 因为个人习惯而言, 我很少用键盘上右边的Shift键, 所以我去掉了所有`SHIFT_R`的映射.

接下来, 我要实现的功能是点击键盘上的快捷键后, 能自动切换程序的窗口. 例如, 同时按下键盘上右边的command键和s, 就会打开safari; 按下键盘上右边的command和i, 就会打开iterm. 实际上, 如果你已经安装了Alfred, 切换程序已经很快了. 比如你在iterm里面写代码, 需要切到safari看下效果, 则可以先``alt-space``打开Alfred输入窗口, 然后输入sa, 接下来回车, 则就可以切换了. 不过我仍嫌这个步骤仍不够快. 因为我们通常关心的应用只有那么几个, 所以没有必要每次呼出Alfred来切换.

具体做法是安装前面说过的seil, 然后将大写锁定键映射80, 将右边的command键映射为79, 对应与怪兽级的全键盘, 分别是`F20`和`F19`这两个功能键. 在我们日常的应用上, 这两个键是没有的. 这样设定是避免冲突. 然后, 我在系统设置里将切换输入法的按键调整成了CapsLock(显示的是F20). 在Karabinerd配置里将F19映射成了Hyper键:

```xml
  <item>
    <name>F18 to Hyper</name>
    <identifier>private.f18tohyper</identifier>
    <autogen>
      __KeyOverlaidModifier__
      KeyCode::F18,
      KeyCode::COMMAND_L, ModifierFlag::OPTION_L | ModifierFlag::SHIFT_L | ModifierFlag::CONTROL_L,
      KeyCode::ESCAPE
    </autogen>
  </item>
```

即, 我按下右边的command, 映射后按下的键是左边的Command/Option/Shift/Control/Escape一起按. 这样, 我的右边的command键就成了一个特殊的修饰键. 我们就能自定义一些组合键, 例如:

```xml
  <!-- safari -->
  <vkopenurldef>
    <name>KeyCode::VK_OPEN_URL_APP_SAFARI</name>
    <url type="file">/Applications/Safari.app</url>
  </vkopenurldef>

  <item>
    <name>Switch to Sarari</name>
    <identifier>private.right_command_s</identifier>
    <autogen>
      __KeyToKey__
      KeyCode::S,
      ModifierFlag::COMMAND_L | ModifierFlag::OPTION_L | ModifierFlag::SHIFT_L | ModifierFlag::CONTROL_L,
      KeyCode::VK_OPEN_URL_APP_SAFARI,
    </autogen>
  </item>
```

这儿, 我先定义了一个特殊的虚拟按键, 功能是呼出Safari. 然后将Hyper-S映射到这个特殊的虚拟按键. 以此, 我们就能够实现文章开头提到的, 按下右边的command和s后调出safari了.

我的具体配置已放在了github上, [这儿](https://github.com/xiaket/etc/blob/master/karabiner.xml)是地址.
