---
title:  "Mac Kung Fu集萃"
date:   2013-06-19 19:51 +0800
lang: zh
ref:    mac-kung-fu
---

下午下班后扫完了[Mac Kung Fu](http://book.douban.com/subject/19996698/)这本书. 这是本没太大必要细读的书, 例如里面关于Finder的说明实在太多, 而Finder是我用得很少的app. 当然, 大浪淘沙后总有些tip对于我还是有点用的.


关掉Trash清空时的声音:

```
defaults write com.apple.finder FinderSounds -bool FALSE;killall Finder
```

命令行下使用通知中心:

```
sudo gem install terminal-notifier
terminal-notifier -message "Mac Kung Fu goes places other books don't dare" -title "Mac Kung Fu"
```

阅读邮件默认使用纯文本. 偶记得这个有个设置项来着, 因为我的邮件都是纯文本. 不过还是记录下吧:
```
defaults write com.apple.mail PreferPlainText -bool TRUE
```

能使用iCloud的app(例如预览, iA Writer等)会默认存到iCloud. 这一点会让一些人(例如我)不爽, 因为我需要每次去将这个改回到本地磁盘. 做了下面这个设定, 默认就是本地磁盘了:

```
defaults write -g NSDocumentSaveNewDocumentsToCloud -bool FALSE
```


全屏状况下鼠标移到dock附近会更快显示隐藏的dock:

```
defaults write com.apple.dock autohide-fullscreen-delayed -bool FALSE; killall Dock
```

Finder的PathBar会默认以Home作为目录起点. (不过话说今天之前我连Finder有PathBar都不清楚...)

```
defaults write com.apple.finder PathBarRootAtHome -bool TRUE;killall Finder
```


降低dock的效果. 我们是从荒芒的Linux世界来到Mac世界的, 对于一切耀眼的东西有天生的嫉恨感:

```
defaults write com.apple.dock no-glass -bool TRUE;killall Dock
```


接入电源时就开始唤醒Mac

```
sudo pmset -a acwake 1
```


关闭DashBoard

```
defaults write com.apple.dashboard mcx-disabled -bool TRUE;killall Dock
```
