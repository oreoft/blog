---
layout: page
title: 中间件学习记录
titlebar: 中间件学习记录
subtitle: <span class="mega-octicon octicon-git-commit"></span>&nbsp;&nbsp;
     <a>一些主流中间件学习记录我会放这里，希望学得越多写的越多懂得越多，嘿嘿😋</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /zh/middleware
lang: zh
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% for post in site.posts %}
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