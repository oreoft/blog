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
    {% assign posts = site.posts | where:"lang", "zh" | sort: "date" | reverse %}
    {% assign current_year = "" %}
    {% for post in posts %}
      {% assign post_year = post.date | date: '%Y' %}
      {% if current_year != post_year %}
        {% assign current_year = post_year %}
        <h3>{{ current_year }}</h3>
      {% endif %}
      <li><span>{{ post.date | date:'%m-%d' }}</span> <a href="{{ post.url }}">{{ post.title }}</a></li>
    {% endfor %}
</ul>