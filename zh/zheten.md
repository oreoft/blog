---
layout: page
title: 折腾分享记录
titlebar: 瞎折腾
subtitle: <span class="mega-octicon octicon-pulse"></span>&nbsp;&nbsp;
     <a>下面是我工作闲暇之余的一些爱好，如果你也感兴趣，欢迎和我一起交流。</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /zh/zheten
lang: zh
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
                {% assign posts = site.posts | where:"lang", "zh"  %}
                {% for post in posts %}
                {% if post.category=='zheten' or post.keywords contains 'zheten' %}
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