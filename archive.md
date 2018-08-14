---
layout: default
---

<article>
  <h3>{%for post in site.posts limit:1 %}{{ post.date | date: "%Y" }}{% endfor %}</h3>
  {% for post in site.posts -%}
    {%- unless post.next -%}
  <ol>
    {%- else -%}
      {%- capture year -%}{{ post.date | date: '%Y' }}{%- endcapture -%}
      {%- capture nyear -%}{{ post.next.date | date: '%Y' }}{%- endcapture -%}
      {%- if year != nyear -%}
  </ol>
  <h3>{{ post.date | date: '%Y' }}</h3>
  <ol>
      {%- endif -%}
    {%- endunless %}
    <li><a href="{{ post.url }}">{{ post.title | escape }}</a><span class="li-date">({{ post.date | date: "%Y-%m-%d %H:%M"}})</span></li>
  {% endfor -%}
  </ol>
</article>
