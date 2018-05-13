---
title:  "这次折腾博客后台所玩过的东西"
date:   2013-03-25 22:45 +0800
lang: zh
---

为了介绍我这次修改所涉及到了的东西, 先介绍一下我这个博客是怎么实现的.

从技术上讲, 现在你所看到的博客是一个静态网站. 其缘起是看到[octopress](http://octopress.org/)这样的东西的存在, 而我之前在wordpress下写博客都是手工写html代码的, 于是我基本用不到Octopress里面的Markdown(好吧实话实说我也不是那么喜欢Markdown). 于是我就该自己写一个博客生成器了. 是的, 这是在重复造轮子, 我知道. 另外, 静态网站还有一个好处是比较容易进行备份, 而且有需要的话, 内容迁移起来很方便. 例如现在我想我可以在一两个小时内将博客服务迁移到类似[farbox](http://www.farbox.com)这样的静态页面服务提供商.

我所使用的编程语言显然是python, 模板语言我用了mako, 当然我想即使是Django的模板语言, 面对这种级别的计算都能很容易地搞定. 我在本地按年份创建了目录们, 并大概制订了一些简单的规范. 而后就只是写一个python脚本按照这个规范, 生成出所需要的html文件了. 我在本地用Makefile来管理运行这些脚本的策略和上传到Linode, 并在本地建立了一个镜像站点来方便各种调试.

前面已经完成的工作不说, 这两三周主要做了这样几件事情:

* RSS订阅链接的生成.
* 全站使用统一的base.template来方便统一地修改nav里的内容.
* 添加样式.
* 添加相册.

#### RSS

我之前到现在的首页都是按时间顺序从新到旧, 放最近的十篇文章. 这个逻辑本身就很类似RSS了. 我添加这个功能所需要做的就是用这一部分内容生成出一个符合RSS规范的xml文件出来, 放在一个固定的地方即可. python可以用来生成RSS feed的库不少, 我在pypi上随便找了一个PyRSS2Gen. 有些小不爽的地方, 但是大体上还过得去. 用这个库开发时需要注意的几点:

* 单篇文章的description可以直接用文章的全部内容了. 反正转成纯文本也不怎么大.
* 单篇文章的pubDate属性最好转换成utc. 这样RSS阅读器会自动帮你计算时间.

理论上, 我在Makefile里应该根据是否有文章被更新来重新生成xml, 而不是每运行一次make就都生成一次, 不过我想这个问题应该不大. 每个文件才不到100K, 压缩后就更小了. 这一点点优化不做也罢.

#### mako继承

这个工作实际上很容易进行. mako的关于这一部分的文档链接是: [http://docs.makotemplates.org/en/latest/syntax.html#include](http://docs.makotemplates.org/en/latest/syntax.html#include). 按照文档试过几次就没什么问题了. 我现在的base.template类似:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/media/blog.css" />
    <link rel="shortcut icon" href="/media/favicon.png">
    <title>${title}</title>
    <%block name="extra_style"/>
</head>
<body>

<div id="page">
<nav>
<a href="/">文章</a>|<a href="/archive.html">存档</a>|<a href="/album.html">相册</a>|<a href="/about.html">关于</a>|<a href="http://weibo.com/xiaket">微博</a>|<a href="http://book.douban.com/people/xiaket/">我读</a>|<a href="/feed.xml">订阅</a>
</nav>
<article>
${self.body()}
</article>
</div>
</body>
</html>
```

而具体到单篇文章, 它的模板就很简单了:

```html
<%inherit file="base.template"/>
<h2>${title}</h2>
<h4 class="pub_date silver">${date}
${body}
```

#### 添加样式

我之前的博客的样式表基本只是reset, 主要的修改是给代码高亮加了一些内容, 另外也给iPhone浏览添加了一些简单的适配. 这样的页面虽然是按HTML5的规范写的, 但是和30年前个人网页刚兴起时的风格近似. 做出这样设定的原因一方面是我懒得去调整, 另一方面是因为我也信奉极简主义. 而这次在添加相册的过程中我不可免地做了很多样式化的工作, 于是一不做二不休直接改掉了全站的样式.

HTML的编写方面没什么好多谈的. 除了前面的模板外基本没改啥, 唯一的例外是添加了一个&lt;article&gt;tag, 让html代码更语义化一点. 这次修改主要做的工作都是在样式表的修改上. 我直接参考了[Skeleton](http://www.getskeleton.com/)的样式表. 没有使用它的类布局方案, 主要参考了它的reset和media-query. 写完reset后, 我对整个页面进行了简单的布局工作, 包括整个的居中, nav这个tag和article的分离, 以及圆角等. 整个html的背景图片来自[Subtle Patterns](http://subtlepatterns.com/)</a>.

接下来是这次做得比较多的移动设备支持的修改, 这些都是通过media-query来实现的. 我没有具体去参考它的定义文档, 只是从一个普通使用者的角度来介绍下: media-query是在样式表中通过对页面最大/最小宽度的识别, 允许设计师为不同的设备使用情况定义不同的样式. 例如对于一台普通的iPhone 4, 正常握持时其页面宽度为320像素, 横放时宽度为480像素. 你就在样式表中根据这些情况有针对性地提高移动设备的用户界面. 在iPhone 4上, 效果如图:

竖排
<img src="/media/2013/iphone4-portrait.png" />

横排
<img src="/media/2013/iphone4-landscape.png" />

上面这些效果都是打开页面后不加任何人手干预的结果, 我想我完全能接受.

值得一提的是, 做出这项样式化后, 站点在IE 9以下的浏览器中阅读效果很差. 我知道这是可以修正的. 但是我之前都曾经动过不允许IE内核的浏览器访问站点的心思, 所以这样的状况我目前比较满意.

#### 添加相册

这一部分工作量最大了, 首先要设计出一个符合我的审美的极简的页面, 然后不停地修改js/css/html来实现. 另外, 后台的代码也值得一提, 毕竟, 图片不会自己放大缩小, 而一个程序员不会允许自己挨个在某个软件里缩小图片的.

先说设计. 我所希望的相册前台应该有下面的主要功能:

* 能够正常展示多个相册的所有图片.
* 图片通过ajax或类似的办法按需加载.
* 页面上展示出的图片应该是完整图片的缩略图, 图片应是jpg格式, 应允许渐进式加载.
* 能够下载原图.
* 浏览器里的链接应适当更新, 适当我们能够根据某个URL来找到它所对应的图片.
* 页面上不应该有上一页/下一页的按钮. 应该点击图片右侧翻到下一页, 点击图片左侧翻到上一页.
* 移动设备上应允许通过滑动来翻页.

后台给相册编辑者的功能应该有:

* 扫描某个文件夹下的所有目录, 每个目录对应一个相册.
* 扫描某个相册目录下的所有图片文件, 自动将新图片添加到该文件夹对应的相册.
* 自动生成一份文本文件, 供管理者编辑, 管理者可以通过编辑这个文件给照片添加注释, 给相册添加名字/时间等.
* 自动生成前述的缩略图.
* 能够以恰当的方式处理竖立的图片.

鉴于后台是前台的基础, 所以我先干后台的活. 关于相册元信息的存储, 我之前考虑过使用sqlite, 但是用peewee写了一段代码后, 我觉得自己还是更熟悉Django的ORM, 而用Django来完成博客的某一个部分感觉有些小题大作. 于是我用纯文本来存这些信息, 这样我编辑起来也方便. 坏处是我得自己解析一个固定的格式, 而且后面扩展起来也比较麻烦. 反正我目前还能接受, 所以先就用文本数据库了.

定下了存数据的方式, 就考虑写脚本来自动获取这些信息了. 我的脚本里定义了三个类, 分别是Site/Album/Photo, 这三个类都有各自的方法. 例如Site里定义了文本数据库的基本格式, 放了从目录更新各个相册的基本逻辑, 以及更新完后写回文本数据库的逻辑等等. Album放某个相册的逻辑, 例如某个相册的发表时间是其下所有相片中最新一张的时间等等. Photo中主要放了图片处理的逻辑. 另外定义一个主函数, 负责实例化一个Site, 读到文本数据库后更新之, 最后写回文本数据库.

其余的不多说, 贴两段图片处理的代码:

```python
    self.exif = {
        ExifTags.TAGS[key]: value
        for key, value in self.img_obj._getexif().items()
        if key in ExifTags.TAGS
    }
    self.date = datetime.strptime(
        self.exif['DateTimeOriginal'],
        "%Y:%m:%d %H:%M:%S",
    )
    self.date = self.date.strftime("%Y%m%d-%H%M%S")
```

前一半是拿到照片所有的EXIF信息, 后面是拿出其中的拍摄时间, 并转成我所需要的时间字符串.

```python
    def write_small(self):
        # calculate new size.
        if self.is_landscape:
            new_height = 400
            new_width = int(new_height * self.width / float(self.height))
            if new_width > 600:
                new_width = 600
                new_height = int(new_width * self.height / float(self.width))
        else:
            new_height = 600
            new_width = int(new_height * self.width / float(self.height))
            if new_width > 400:
                new_width = 400
                new_height = int(new_width * self.height / float(self.width))

        # normalize.
        if 600 - new_width < 3:
            new_width = 600
        if 400 - new_height < 3:
            new_height = 400

        ImageFile.MAXBLOCK = 1200 * 800
        target_image = Image.new('RGBA', (600, 400), "white")
        thumbnail = self.img_obj.copy()
        thumbnail.thumbnail(
            (new_width, new_height), Image.ANTIALIAS,
        )
        new_width, new_height = thumbnail.size

        left, right, upper, lower = 0, 600, 0, 400

        if new_height != 400:
            # set upper, lower
            upper = (400 - new_height) / 2
            lower = upper + new_height
        if new_width != 600:
            # set left, right
            left = (600 - new_width) / 2
            right = left + new_width
        self.shift = left

        target_image.paste(thumbnail, (left, upper, right, lower))
        small_image = open(self.small_path, 'w')
        target_image.save(
            small_image, "JPEG",
            quality=100, optimize=True,
            progressive=True,
        )
```

这个函数略长一点儿. 大概依次做了下面这几件事情:

1. 计算按比例缩放后缩略图的真实大小
1. 归一化一下, 有时候1200*800的图片的缩略图大小会算成600*399.
1. 生成一个600*400的样板, 涂白, 然后把缩小后的图片贴到里面去, 居中. 这样就不那么完美地处理了竖排图片的问题.
1. 写缩略图成文件. 这儿的quality是最高值, progressive表示允许渐进方式打开(随着浏览器对图片的下载, 图片越来越清楚).

后台的工作大概就是这样了. 另外, 为了让前台能够获取到所有相册的照片信息, 我在后台还生成了一个json文件, 供前台Ajax获取.

下面来说前台.

我首先考虑了移动设备上滑动翻页的需求, 找到了<a href="http://swipejs.com">Swipejs</a>, 这个js库能够做这个事情. 于是, 不多想了, 后面的开发都是基于这个库进行的. 浏览器里的链接刷新问题可以用锚点解决. 我用类似下面的js实现了对URL的解析, 拿到用户所希望看到的相册和图片:

```javascript
function parse_url(){
  // parse anchor in url, find requested album name and photo_position;
  var url = $(location).attr('href');
  var index = url.indexOf('#');
  if (index === -1){
    // no anchor found, use first album.
    window.album_name = $(".album:eq(0)").attr("id");
    var position = 0;
  }else{
    var anchor_text = url.substr(index + 1);
    var _index = anchor_text.lastIndexOf('_');
    if (_index === -1){
      // no photo selected. use first photo.
      var position = 0;
      window.album_name = anchor_text;
    }else{
      var position = parseInt(anchor_text.substr(_index + 1));
      window.album_name = anchor_text.substr(0, _index);
    };
  };
  return position;
}
```

思路很简单, 就是拿到当前链接后用js做一下字符串处理而已. 另外我显然也需要在每次图片载入完毕后更新URL:

```javascript
window.location.href = "#" + album_name + "_" + selected_album.getPos();
```

这样, 我就成功地把后端的活放到前端用javascript干. 接下来, 我来实现页面切换的功能. 前面说了, 我会用swipejs, 于是在移动设备下的切换可以忽略了. 而对于没有swipe事件的普通电脑浏览器而言, 我们要做的还有不少.

我本来设想将一个a元素放到swipe的类里面, a里面再放img元素, 加载图片. 为实现按需加载, 可以动态的根据swipe提供的接口来改变img元素的src属性. 这样做的好处是我可以简单地设定一个map来把上一页, 下一页的超链接映射到图片上, 这个方案很自然. 不好的地方在于对于移动设备, 这个相册的宽度不容易做到自适应. 我得对于每个设备宽度写图片宽度设置. 最后我采用的方案是把图片设为一个div的背景图. 这样我对于移动端只需要设定整个页面宽度就可以了, 不用再去处理这个细节. 不足之处是无法使用map来映射超链接, 不过这个问题也能够得到解决:

```javascript
  // add click events to navigate through slides.
  $("#selected_album div[imgsrc]").unbind('click');
  $(_element).click(function(e) {
    var posX = e.pageX - $(this).offset().left;
    var posY = e.pageY - $(this).offset().top;
    if (posX > 200){
      selected_album.next();
    }else{
      selected_album.prev();
    }
  });
```

上面这段代码就是通过读到鼠标在当前div上的相对位置而算出在现在这个地方点击是跳到上一页还是下一页.

最后一个要实现的需求是原图的下载. 这个可以在页面上某个地方加一个超链接来实现, 但是我不喜欢. 这样够明显但不够简单. 我实现的方式是在图片上添加了一个水印一样的图片, 点击这个图片实现对图片的下载.
