---
layout: page
title: 忘川
lang: lang-zh-hans
permalink: /novels/wangchuan/
---

至元二十一年秋, 集贤院书吏王遵礼奉命南下搜访旧档, 在会稽城东一棵老槐树下遇见了一个叫陆承影的老人. 老人说, 旧事嘛, 你想听, 听听就好.

---

{% assign chapters = site.novels | where: "novel", "wangchuan" | sort: "order" %}
<ul>
{% for chapter in chapters %}
  <li><a href="{{ chapter.url }}">{{ chapter.title }}</a></li>
{% endfor %}
</ul>
