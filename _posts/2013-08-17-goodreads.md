---
title:  "从www.goodreads.com爬书籍信息"
date:   2013-08-17 22:39 +0800
lang: zh
ref:    goodreads
---

今天网上乱晃时找到一个7.6G的Kindle书籍合集, 解压后有9.1G, 3500个作者的9000本书. 为了筛选这些英文小说, 必须要用自动化的办法...

首先需要确定的是, 这种英文小说的评分需要从国外网站拿, 国内唯一可靠的书籍评分源头是豆瓣, 不过它的专长显然不是这种英文小说. 于是搜了下, 找到[www.goodreads.com](http://www.goodreads.com)这个站点. 貌似在上面评分的人还不少. 下一步就是去取书籍信息和评分了.

这个压缩包是某个人的calibre图书馆, 好处在于这些书籍都分门别类地放好了. 一个作者一个目录, 目录下有一本或数本书籍, 每本书籍又是一个目录. 书籍目录里面有书籍文件, 书籍的封面, 以及书籍的元信息文件(.opf文件). 拿到这些书籍信息只是一些简单的shell脚本活, 大部分opf文件里面都有书籍的isbn号, 于是我们可以根据这个isbn来去向goodreads发API请求. 拿到信息, 然后再处理一下就行了.

逻辑就是这么简单, 放代码吧:

```sh
#!/bin/sh
#
# Author:         Xia Kai <xiaket@corp.netease.com/xiaket@gmail.com>
# Filename:       getbookrating.sh
# Date created:   2013-08-17 21:40
# Last modified:  2013-08-17 22:51
#
# Description:
#

KEY="getyourownkey"
IFS=$'\n'

for author in `gls -l | grep "^d" | cut -c 51-`
do
    for bookdir in `gls -l ./"$author" | grep "^d" | cut -c 44-`
    do
        sleep 1
        dir_path="$author/$bookdir"
        isbn=`grep -i isbn $dir_path/metadata.opf | egrep -o "\d+"`
        if [ $? -eq 0 ]
        then
            json=`curl --retry 3 "http://www.goodreads.com/book/review_counts.json?isbns=$isbn&key=$KEY" 2>/dev/null`
            if [ $json = "No books match those ISBNs." ]
            then
                echo "WARN: " $dir_path "not found!"
                continue
            fi
            echo "DEBUG: " $json
            rating=`echo $json | python -c "import json, sys; print json.loads(sys.stdin.read())['books'][0]['average_rating']"`
            count=`echo $json | python -c "import json, sys; print json.loads(sys.stdin.read())['books'][0]['ratings_count']"`
            if [ `echo "$rating - 4." | bc | cut -c 1` = '-' ]
            then
                echo "WARN: " $dir_path $rating $count
            else
                echo "GOOD: " $dir_path $rating $count
            fi
        else
            echo "ERROR: book isbn not found:" $dir_path
        fi
    done
done
```

一开始这儿拿作者和拿书籍目录都可以用find来做, 不过没这么做. cut在这儿用来处理ls -l的输出很舒服. 接下来从.opf文件里面拿到书籍的isbn信息用了两次grep, 一次拿出这一行来, 一次找出具体的isbn. 接下来, 网络比较慢, 只能在curl里面加上一个重试的参数. 跑了一两次脚本中发现如果书籍找不到, goodreads的API会返回一个字符串提醒你. 如果我们真的拿到json内容了, 用bash处理显然是不合适的, 用python来处理就方便多了. 拿到评分后用bc计算一下, 来为后面进一步筛选做准备.

整个脚本的编写加调试花了一个小时出头, 顺便给我的header插件打个广告. 看到脚本前面的注释了咩? 这个是自动生成的. 具体插件及文档在[https://github.com/xiaket/better-header](https://github.com/xiaket/better-header)可以看到.

最后, 是的, 我知道, 即使筛选出来, 我也不一定会去读这些书的...
