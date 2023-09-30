---
layout: page
title: artifact
titlebar: artifact
subtitle: <span class="mega-octicon octicon-pulse"></span>&nbsp;&nbsp;
     <a>Fascinated by efficiency tools, like to explore more ways to play not only to meet the simple use, so good to use, why repeat the building of the wheel?</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /tools
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
                {% if post.category=='tools' or post.keywords contains 'tools' %}
                <li class="posts-list-item">
                    <div class="posts-content">
                        <span class="posts-list-meta">{{ post.date | date: "%Y-%m-%d" }}</span>
                        <a class="posts-list-name bubble-float-left" href="{{ post.url }}">{{ post.title }}</a>
                        <span class='circle'></span>
                    </div>
                </li>
                {% endif %}
            {% endfor %}
        </ul> 

        <!-- Pagination -->
        {% include pagination.html %}

        <!-- Comments -->
       <div class="comment">
         {% include comments.html %}
       </div>
    </div>

</div>
<script>
    $(document).ready(function(){

        // Enable bootstrap tooltip
        $("body").tooltip({ selector: '[data-toggle=tooltip]' });

    });
</script>