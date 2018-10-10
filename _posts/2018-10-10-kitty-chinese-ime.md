---
title:  自编译Kitty支持中文输入"
date:   2018-10-10 20:58 +1000
lang:   zh
ref:    kitty-chinese-ime
---

前文说了, kitty目前的中文输入有问题. 表现在拼音选字框中选定了字后不会出现在kitty里面. 我之前一直以为这是一个比较底层的问题, 结果发现并不是. 昨天我在翻kitty已经关闭的issue, 看看有没有合适的kitten主意, 想自己写写练练手. 结果看到[这个issue里的讨论](https://github.com/kovidgoyal/kitty/issues/910). 很可惜, 作者不太愿意通过一个简单的hack来实现这个功能, 我能理解他的立场, 毕竟, 输入法的处理本应该在GUI库那一层处理掉, 但是kitty依赖的[glfw一直没能解决好这个问题](https://github.com/glfw/glfw/issues/41)(啧啧, 一个五年前的老issue). 你要一个应用层的东西去处理一个框架级别的缺陷也的确不算合适.

作者自己主要在Linux下做开发工作, 所以他给kitty用的glfw库打了补丁, 支持了ibus. 可惜的是, macOS下的中文输入就只能自食其力了. 换位思考下, 作者第一自己不用中文输入, 第二自己不怎么用macOS, 第三还要维护calibre和kitty, 没时间来搞mac下中文输入这个在他看来吃力不讨好的事情. 而且作者的态度也是很明确的, 这个坑我自己不会去填, 你们谁有意愿去填坑, 而且代码过得去, 那么我乐意接受PR. 可惜我自己从没玩过cocoa编程(现在要我去macOS下玩app开发也不会去学cocoa不是), 所以没能力写代码实现这个功能造福社会了. 不过有人指出, 只要删掉三行代码和中文输入完全无关的代码, 中文输入法的问题也能大致解决了. 所以写了下面这段代码来自己打包kitty:

```bash
#!/bin/bash

# A script to:
#   1. update kitty from kovidgoyal/kitty
#   2. apply the patch provided by blahgeek here:
#       https://github.com/kovidgoyal/kitty/issues/910

set -o errexit
set -o nounset
set -o pipefail


default () {
  update && build && clean
}

prepare () {
  # prepare build env in macOS.
  brew install harfbuzz --without-graphite2 --without-icu4c --without-freetype
  brew install imagemagick optipng librsvg
}

build () {
  git apply chinese.patch
  make app
  tar czf kitty.app.tgz.$(date +"%Y-%m-%d") -C /Applications kitty.app
  rm -rf /Applications/kitty.app
  cp -r kitty.app /Applications
}

update () {
  if ! git remote | grep --quiet upstream
  then
    git remote add upstream git@github.com:kovidgoyal/kitty.git
  fi
  git fetch upstream
  git checkout master
  git merge upstream/master
}

clean () {
  rm -r kitty.app.tgz.*
  rm -rf kitty.app
  git co -- glfw/cocoa_window.m
}

list () {
  grep -E "()\ ?{$" $0 | grep -v 'grep ' | awk '{print $1}' | sort
}

# main start here
command=${1:-""}

if [ -n "$(type -t $command)" ] && [ "$(type -t $command)" = function ]
then
  shift
  eval $command "$@"
  exit $?
fi

case "$command" in
  *)
    default
esac
```

打包逻辑只是将[作者的文档](https://sw.kovidgoyal.net/kitty/build.html)代码化而已, 不予赘述. 倒是整体操作的方式值得一提: 我将原始项目fork到自己的命名空间下, 本地加上一个原项目中不存在的`manage`脚本和一个`chinese.patch`文件, 这样, 我还可以完全无障碍地从上游项目将作者最新的改动更新到本地来使用, 也能保证中文输入在所有这些版本中都可用.

另, 上面这段代码的boilerplate来源于我自己维护的一个项目, [manages](https://github.com/xiaket/manages). 我见过太多把Makefile当做项目入口脚本的项目了. 我自己对Makefile的语法又是深恶痛绝, 所以挖了这个小坑, 概念是把这个manage脚本放到项目根目录下, 在里面加上一群bash函数来写功能. 在使用时, 直接使用`./manage function_name`来运行这个bash函数就可以了. 例如, 在manage脚本里加上一个clean函数, 把清理项目临时文件的逻辑放到里面, 然后每次无脑运行`./manage clean`就行了.

最后顺口说下, 这个简单的patch实际上并不是完全没问题的, 拼音输入状况下如果按退格删除当前拼音输入的内容, kitty除了删掉拼音选字栏中的当前字母, 还会删除当前行的一个字. 例如, 我在kitty里面输入了“最后顺口", 并且输入了`tiyij`, 这时我改变了主意, 不准备写成"提一句", 而是改成"说下". 我们的拼音习惯会让我输入五个退格键, 然后输入`shuox`, 对吧? 在正常的程序里面, 这样操作是没问题的. 但是在kitty里面, 当你输入了第一个退格键时, 当前行会变成"最后顺", 选字框中的拼音会是`tiyi`. 一个退格在两个地方起了作用. 对此, 我暂时是无能为力的, 凑活着用吧.
