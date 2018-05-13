---
layout: default
---

<article>
<ol id="main_ol">
{% for post in site.posts limit:10 %}<li><a href="{{ post.url }}">{{ post.title | escape }}</a> ({{ post.date | date: "%Y-%m-%d %H:%M"}})</li>
{% endfor %}
</ol>
</article>
