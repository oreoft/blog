---
layout: page
title: Catch All
titlebar: Gather
subtitle: <span class="mega-octicon octicon-calendar"></span>&nbsp;&nbsp;
     <a>All the articles on this site will be displayed here according to the actual time without categorization.</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /en/archives/
lang: en
---

<ul class="archives-list">
  {% assign posts = site.posts | where:"lang", "en" | sort: "date" | reverse %}
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