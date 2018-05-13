---
title:  "将iTunes正在播放的歌曲发布到新浪微博"
date:   2011-09-25 21:08 +0800
lang: zh
---

今天无聊时申请了一个新浪微博的马甲, 不知道能拿来干什么, 于是想到可以做个简单的新浪微博应用出来给自己玩. 想来想去就搞了个python脚本将iTunes里面正在播放的歌发布到微博.

首先玩后端的工作, 要拿到iTunes的播放状态, 在Windows平台下用win32com来搞. 具体样例代码可以参考[ActiveState上的这篇帖子](http://code.activestate.com/recipes/498241-scripting-itunes-for-windows-with-python/). 另外, [iTunes官方提供的SDK](http://connect.apple.com/cgi-bin/WebObjects/MemberSite.woa/wa/getSoftware?bundleID=20139)里的帮助文件也是必不可少的.

开了一个Idle, 花了一点点时间就能够摸到怎样拿到正在播放的歌曲的基本信息了:

```python
>>> from win32com.client import Dispatch
>>> itunes = Dispatch("iTunes.Application")
>>> ct = itunes.CurrentTrack
>>> print ct.Name, ct.Artist
Einaudi: Fly Ludovico Einaudi
```

好了, 我们现在可以整理一下需求了, 我们希望发出来的微博是什么样子的: 首先无疑问应该包含歌曲名称, 专辑名称, 演唱者名字, 已播放次数. 如果当前是在一个播放列表里播放, 那么播放列表的名字也是应该之选. 如果当前歌曲有专辑封面, 上传专辑封面也是一个很好的选择. 来来来, 我们格式化一下:

```
#Now Playing# Einaudi: Fly - Ludovico Einaudi, 专辑<divenire>, 播放列表'favourite', 当前歌曲已播放59次.
</divenire>
```

貌似长度还行. 应该不会超过140字的限制. 我们想想代码怎么实现吧. 首先要确定的是, 我们应该把歌曲的信息尽量压榨出来, 做成字典传给待格式化的字符串, 这样如果我们对当前格式化字符串有不满, 添加属性到微博内容的时候也可以尽量少地改动代码. 在iTunes官方提供的SDK里面, 我们把这些歌曲的属性都拿出来:

```python
from win32com.client import Dispatch


itunes = Dispatch("iTunes.Application")
track = itunes.CurrentTrack
track_info = {
    'name': track.Name,
    'artist': track.Artist,
    'playlist': track.Playlist.Name,
    'album': track.Album,
    'dateadded': track.DateAdded.Format(),
    'duration': track.Duration,
    'genere': track.Genre,
    'playedcount': track.PlayedCount,
    'rating': track.Rating,
    'size': "%.1fM" % (track.Size / 1024. /1024),
    'year': track.Year,
    'time': track.Time,
}
```

这段写好以后, 要完成我们之前说的微博内容是很容易的:

```python
post_content_format = u"#Now Playing# %(name)s - %(artist)s, 专辑&lt;%(album)s>, 播放列表'%(playlist)s', 已播放%(playedcount)s次"

post_content = post_content_format % track_info
```

对哦, 我们还需要歌曲的专辑封面. 于是继续围观SDK的帮助文档, iTunes不会给你目前这个专辑封面在硬盘上的文件名, 而是只提供了一个另存的接口:

```python
artwork = track.Artwork
if artwork.Count > 0:
    format_dict = {
        0: 'Unknown',
        1: 'jepg',
        2: 'png',
        3: 'bmp',
    }
    picobj = artwork.Item(1, pic)
    pic_format = picobj.Format

    if pic_format in [0, 3]:
        # 这两个格式不被新浪微博支持.
        return {'status': status}
    else:
        temp_dir = os.environ['TEMP']
        pic_name = '%s\artwork.%s' % (temp_dir, format_dict[pic_format])
        picobj.SaveArtworkToFile(pic_name)
```

到现在, 我们已经完成了iTunes这边的工作. 接下来该玩玩新浪微博的API了. 由于之前没玩过oauth, 于是先对照代码看了看文档. python的SDK给我感觉应该是某个人(比较有可能是新浪工作人员)在jroesslein的Twitter python SDK(Tweepy)的基础上修改而成的. 本来Tweepy的代码就看得我不爽, 改编者又使代码质量下降不少. 我本来想在已有pythonSDK的基础上改改, 后来由于这个原因还是自己重写了下. 一个文件把oauth, API请求以及各种细节处理全放下了, 行数也只有300左右. 还算满意了.

写这个python脚本过程中玩了几样东西. 一是oauth, 这个不提, 基本就是照着文档来写就可以了. 新浪的API服务器比较厚道, 如果你签名有问题, 服务器会给一些比较有帮助的调试信息出来. 二是玩了webbrowser模块, 这个东西在Windows下用还是挺不错的. 三是做了件恶心的事情: 由于oauth签名的关系, 新用户会从服务器拿到访问密钥. 这两个字符串不好保存, 于是我通过写临时文件再重命名把这两个字符串写到自身里面了. 自己再做些判断, 如果这两个变量被设置了就不再去请求这个权限.

代码中肯定还有各种小问题, 先不管, 以后遇到再修吧~

[代码](/media/2011/itunes-playing.py)

实际效果: <img src="/media/2011/demo.png"/>
