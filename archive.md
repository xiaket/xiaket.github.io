---
layout: default
---

<article>
  {% for post in site.posts %}
  {% assign currentdate = post.date | date: "%Y" %}
  {% if currentdate != date %}
    {% unless forloop.first %}</ol>{% endunless %}
    <h3>{{ post.date | date: "%Y" }}</h3>
  <ol>
    {% assign date = currentdate %}
  {%- endif -%}
    <li><a href="{{ post.url }}">{{ post.title | escape }}</a><span class="li-date">({{ post.date | date: "%Y-%m-%d %H:%M"}})</span></li>
  {% if forloop.last %}</ol>{% endif %}
  {% endfor %}
</article>
