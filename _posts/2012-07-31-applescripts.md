---
title:  "一些自用AppleScript脚本"
date:   2012-07-31 15:15 +0800
lang: zh
---

换到Mac下工作, 一些原来写的脚本就不能用了, 很多操作习惯需要修改适应, 这个过程比较痛苦. 作为一个<abbr title="System Administrator">SA</abbr>, 我几年来都是在[konsole](http://konsole.kde.org/)下进行日常工作的, 现在切换到Mac下, 一群快捷键不能使用是一个大问题.

例如, 我做开发的时候习惯开多个tab, 然后用Meta+S来给每个tab进行重命名, 提醒自己这个tab是用来干啥的. konsole的这个功能在iTerm2下没有了. 好吧, 要说还是有的, 例如你可以双击一个tab, 会出来一个对话框来让你改名. 我当然可以给这个功能绑定一个快捷键, 不过我实在不喜欢这个对话框, 它太大, 可以修改的东西太多, 会扰乱我的思路. 于是, 我倒腾了下面的脚本来完成这个工作:

```applescript
tell application "iTerm 2"
    activate

    set current_name to the name of current session of current terminal
    display dialog "Rename Tab" default answer current_name
    set newname to (text returned of result)
    tell current session of current terminal
        set name to newname
    end tell
end tell
```

给这个脚本绑定一个快捷键, 大概也就能完成我要的需求了:

<img src="/media/2012/rename_tab.png"/>

另一方面是自己之前写过的一个切换konsole编码的脚本不能用了, 这是个大问题. 写之前这个脚本的需求是我们经常需要在GBK和UTF-8编码之间切来切去. 在完成这个脚本后, 遇到编码问题我就按快捷键, 如果当前是某一个编码就切换到另外一个. 脚本如下:

```bash
#!/bin/bash

current_session=`qdbus org.kde.konsole /Konsole currentSession`

current_encoding=`qdbus org.kde.konsole /Sessions/$current_session codec`

if [ $current_encoding == "GBK" ]
then
    qdbus org.kde.konsole /Sessions/$current_session setCodec UTF-8 > /dev/null
else
    qdbus org.kde.konsole /Sessions/$current_session setCodec GBK > /dev/null
fi
```

脚本本身没什么好解释的, 简单dubs编程而已. 不过因为iTerm2本身的限制, 我没办法做类似的事情. 于是我向iTerm2提交了[一个ticket](http://code.google.com/p/iterm2/issues/detail?id=2044&start=500), 作者目前希望能在3.0版本中加入这个特性, 不过这个就真不知道要等多长时间了. 目前只好凑合着用.

昨天又折腾了下通讯录, 将以前Thunderbird中的通讯录文件导入到系统自带的通讯录中, 另外和手机中的通讯录进行合并, 为此又弄了两个脚本. 加上通讯录自带的智能列表功能,  算是能正常使用了.

首先是为某个智能列表中的所有人设置属性公司为NTES, 用下面的脚本:

```applescript
tell application "Contacts"
    activate
    repeat with this_person in every person of group "mail"
        set organization of this_person to "NTES"
    end repeat
    save
end tell
```

脚本本身没什么好解释的, 一个循环而已.

另一个脚本是把通讯录中人名的名和姓分开, 具体代码如下:

```applescript
tell application "Contacts"
    activate
    repeat with this_person in every person of group "fix_name"
        set fullname to (first name of this_person) as string
        get fullname
        set fname to character 1 of fullname
        set len_of_fname to length of fullname
        try
            set lname to (characters 2 thru len_of_fname of fullname) as string
        on error
            set lname to character 2 of fullname
        end try

        set last name of this_person to fname
        set first name of this_person to lname
    end repeat
    save
end tell
```
