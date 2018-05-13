---
title:  "Mac下创建有声书"
date:   2014-03-03 14:18 +0800
lang: zh
---

本文介绍最近的折腾, 主要是如何高效地在Mac下创建有声书, 这包括:

* 将电影里的音频流提取出来得到一个有声书.
* 合并一群mp3文件, 得到一个单一的mp3文件.

### 软件准备

首先安装写必须的软件包, 首先需要安装[Homebrew](http://brew.sh), 然后安装ffmpeg和mplayer.

```sh
brew install ffmpeg mplayer
```

关于mp3的合并, 本有另一个软件名为[mp3wrap](http://mp3wrap.sourceforge.net/), 不过这个软件我不喜欢它命令行参数指定的方式, 而且生成出的文件也不一定靠谱(在音频纠错上有些问题, 导致iTunes卡死或提前中断), 于是没有安装它. 反正ffmpeg也能用来合并mp3文件.

### 音频提取

我们首先把视频中的音频提取出来, 这个我[之前](/2010/notes-on-ffmpeg.html)就做过. 这一次只是整理了一下代码, 加入了音频质量判断的逻辑:

```sh
DEFAULT_SAMPLE_RATE=32000
DEFAULT_BIT_RATE=80

fullpath="$1"
filename=`basename "$fullpath"`
suffix=`echo "$filename" | awk -F '.' '{print $NF}'`
basename=`basename "$filename" $suffix`
temp_name="${basename}mp3"
output_name="${basename}m4b"

mediainfo=`mplayer -endpos 0 -vo null -ao null "$fullpath" 2>/dev/null | grep "^AUDIO"`
bit_rate=`python -c "br = '${mediainfo}'.split(',')[3].strip().split()[0]; print min(br, ${DEFAULT_BIT_RATE})"`

ffmpeg -i "$fullpath" ${temp_name}
```

这样就能创建出一个临时的mp3文件, 里面是电影的音频, 我们后面会将这个文件转换成m4b的有声书格式.

### mp3合并

前面说了, 用mp3wrap合并mp3并不算好的方法. 用ffmpeg合并音频的办法是:

```sh
ffmpeg -f concat -i files.list -c copy output.mp3
```

这儿的files.list应该是一个固定格式的文件. 里面包含需要合并的文件的信息. 为了生成这个列表, 需要一些简单的编码工作:

```sh
TEMPFILE=mp3join.list
OUTPUT="./output.mp3"
rm -f $TEMPFILE

python -c "import os; open('${TEMPFILE}', 'w').writelines(['file \'%s\'\n' % file.replace("'", "\\'") for file in os.listdir('.') if file.endswith('.mp3')])"

if [ -f $OUTPUT ]
then
    echo "file exist, quit"
    exit 1
fi

ffmpeg -f concat -i "$TEMPFILE" -c copy output.mp3

rm $TEMPFILE
```

这个脚本没啥复杂的, 就不解释了. 顺便想吐槽下, 我合并的时候有个文件的文件名里有一个英文单引号, 运行时导致ffmpeg抛了一个segmentation fault, 真是让人觉得堪忧. 我手工加了一个处理逻辑, replace了文件名中可能的单引号, 强行加了一个转义字符进去. 上面这个脚本我保存到自己放自己编写的命令的目录下, 使用的时候cd进到需要合并的mp3所在的文件夹, 然后执行一下这个脚本就行了.

### mp3转换成m4b文件

之前我拿到mp3后都是导入到iTunes里面, 用iTunes自带的转换功能转换成aac编码的m4a文件, 然后再去目录里重命名成m4b文件. 这次找到了一个苹果自带的命令来进行格式的转换: afconvert. 执行转换的参数类似:

```sh
afconvert "${fullpath}" -v -s 3 -o "${output_name}" -q 127 -b "${bit_rate}000" -f m4bf -d aach
```

这个命令输出的m4b文件就可以直接导入到iTunes里了.

### 脚本

上面说了三个部分, 一个是视频提取, 一个是mp3合并, 一个是mp3转成m4b文件. 这儿分成了两个脚本, 一个是2m4b, 负责将输出的文件转换成m4b文件; 另一个是mp3join, 只负责合并. mp3join已经贴在前面了, 这儿只需要2m4b:

```sh
#!/usr/bin/env bash
#
# Author:         Xia Kai <xiaket@corp.netease.com/xiaket@gmail.com>
# Filename:       2m4b
# Date created:   2014-02-27 16:52
# Last modified:  2014-02-27 16:52
# Modified by:    Xia Kai <xiaket@corp.netease.com/xiaket@gmail.com>
#
# Description:
# create an m4b audiobook file from a movie or an mp3 file.
# Changelog:
# 2014-02-28 11:28: added mp3 support.

DEFAULT_SAMPLE_RATE=32000
DEFAULT_BIT_RATE=80

fullpath="$1"
filename=`basename "$fullpath"`
suffix=`echo "$filename" | awk -F '.' '{print $NF}'`
basename=`basename "$filename" $suffix`
temp_name="${basename}mp3"
output_name="${basename}m4b"

mediainfo=`mplayer -endpos 0 -vo null -ao null "$fullpath" 2>/dev/null | grep "^AUDIO"`
bit_rate=`python -c "br = '${mediainfo}'.split(',')[3].strip().split()[0]; print min(br, ${DEFAULT_BIT_RATE})"`

if [ $suffix = "mp3" ]
then
    afconvert "${fullpath}" -v -s 3 -o "${output_name}" -q 127 -b "${bit_rate}000" -f m4bf -d aach
else

    ffmpeg -i "$fullpath" "${temp_name}" && afconvert "${temp_name}" -v -s 3 -o "${output_name}" -q 127 -b "${bit_rate}000" -f m4bf -d aach && rm "${temp_name}"
fi
[/code]
```

这个脚本最新的版本在[这儿](https://github.com/xiaket/etc/blob/master/bin/2m4b)可以看到.
