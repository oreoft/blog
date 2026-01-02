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
  {% assign posts = site.posts | where:"lang", "en"  %}
  {% for post in posts %}

    {% unless post.next and post.next.lang == 'en' %}
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