---
layout: default
---

<article>
<ol id="main_ol">
{% for post in site.posts limit:10 %}<li><a href="{{ post.url }}">{{ post.title | escape }}</a><span class="li-date">({{ post.date | date: "%Y-%m-%d %H:%M"}})</span></li>
{% endfor %}
</ol>
</article>
