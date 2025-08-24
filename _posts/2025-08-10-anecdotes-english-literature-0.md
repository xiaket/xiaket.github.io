---
title:  八卦英国文学史 - 序言
date:   2025-08-10 10:24
ref:    anecdotes-english-literature-0
series: anecdotes-english-literature
series_order: 0
---

二十多年前, 我在学校里读书的时候, 就在bbs上读完了ukim写的[Heroes in my heart](http://staff.ustc.edu.cn/~yqliang/files/teaching/Heroes.pdf), 很是欣赏. 最近, 我在做一些伦敦旅游的调研, 在本地图书馆里找到了一本讲英国文学八卦的书, [Literary London](https://www.goodreads.com/book/show/29501396-literary-london), 读起来很是兴致盎然. 所以一时技痒, 参考Heroes in my heart, 按个人喜好选取Literary London里的一些更有趣的故事, 编撰了这份文档, 供各位看官茶余饭后一笑.

在您正式开始读之前, 我想废话几句.

首先, 读八卦不等于读原著, 这份文档能够让您知道一些名字, 要真正了解这些作家, 还得回到原著里面去. 你真的可以通过读书来了解一个作家和他/她的审美. 所以, 请不要在囫囵吞枣了这些八卦后志得意满.

有人说, 实在读不下去怎么办? 我会建议你换一本读, 或者换一个作家读. 如果是读中文翻译版本, 换一个译者有时候也挺管用. 或者在时间尺度上, 放几年再读也行. 说来惭愧, 我自己读拉什迪, 读塞林格, 读马尔克斯, 甚至读托尔金, 都读不下去, 原因各异. 但这也不妨碍我去读其他的作者的作品.

最后, 读了这些书又能怎么样呢? 怎么也不可能让我一日之内舌灿莲花或者加官晋爵对吧? 这是一个好问题, 但是我相信卡尔维诺一定回答得比我好. 您可以在[这儿](https://www.ruanyifeng.com/calvino/2007/09/why_read_the_classics.html)看看他是怎么说的. 按我的理解, 我们可以拿武侠小说来打比方, 读经典类似练内力而不是招式. 笑傲江湖开头时, 令狐冲虽然有精妙绝伦的独孤九剑傍身, 但是战力仍是堪忧. 直到学晓了易筋经, 才能与天下英雄一较高下.

最后, 衷心希望您能喜欢这些故事. ;)

### 系列文章目录

{% assign series_posts = site.posts | where: "series", "anecdotes-english-literature" | sort: "series_order" %}
{% for post in series_posts %}
{% unless post.series_order == 0 %}
- [{{ post.title }}]({{ post.url }})
{% endunless %}
{% endfor %}
