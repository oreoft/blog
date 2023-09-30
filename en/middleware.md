---
layout: page
title: Middleware Learning Record
titlebar: Middleware Learning Record
subtitle: <span class="mega-octicon octicon-git-commit"></span>&nbsp;&nbsp;
     <a>Some mainstream middleware learning records I will put here, I hope to learn more write more know more, hehehe 😋</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /middleware
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
            <!-- 以后完善了更多的中间价需要在这里加入，把这个包进去 -->
                {% if post.category=='middleware' or post.keywords contains 'redis' or post.keywords contains 'mysql' or post.keywords contains 'redis' or post.keywords contains 'redis' or post.keywords contains 'redis' %}
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