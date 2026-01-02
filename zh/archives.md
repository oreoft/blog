---
layout: page
title: 一网打尽
titlebar: 汇总
subtitle: <span class="mega-octicon octicon-calendar"></span>&nbsp;&nbsp;
     <a>本站所有的文章都会不分类按照实际时间展示在此</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /archives/
lang: zh
---

<ul class="archives-list">
    {% assign posts = site.posts | where:"lang", "zh"  %}

    {% for post in posts %}

    {% unless post.next and post.next.lang == 'zh' %}
      <h3>{{ post.date | date: '%Y' }}</h3>
    {% else %}
      {% capture year %}{{ post.date | date: '%Y' }}{% endcapture %}
      {% capture nyear %}{{ post.next.date | date: '%Y' }}{% endcapture %}
      {% if year != nyear %}
        <h3>{{ post.date | date: '%Y' }}</h3>
      {% endif %}
    {% endunless %}

    <li><span>{{ post.date | date:'%m-%d' }}</span> <a href="{{ post.url }}">{{ post.title }}</a></li>
  {% endfor %}
</ul>