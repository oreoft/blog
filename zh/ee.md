---
layout: page
title: 电工基础
titlebar: 一丢丢电工知识
subtitle: <span class="mega-octicon octicon-tools"></span>&nbsp;&nbsp;
     <a>天天听B站南桥赌神的笔记本维修厮的绿波电龙，对这块很好奇，所以会找资料学习。
     <br/>可能有一些经授权的学习文章会转载到这里</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /zh/ee
lang: zh
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
                {% assign posts = site.posts | where:"lang", "zh"  %}
                {% for post in posts %}
                {% if post.category=='ee' or post.keywords contains 'ee' %}
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