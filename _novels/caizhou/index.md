---
layout: page
title: 蔡州
lang: lang-zh-hans
permalink: /novels/caizhou/
---

端平元年正月, 宋蒙联军破蔡州, 金哀宗自缢. 百年社稷一朝而绝, 靖康以来未雪之耻, 至此终了. 随军记室周让亲历此役, 这是他的故事, 也是每个人的故事.

---

{% assign chapters = site.novels | where: "novel", "caizhou" | sort: "order" %}
<ul>
{% for chapter in chapters %}
  <li><a href="{{ chapter.url }}">{{ chapter.title }}</a></li>
{% endfor %}
</ul>
