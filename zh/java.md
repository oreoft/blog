---
layout: page
title: Java学习
titlebar: Java学习记录
subtitle: <span class="mega-octicon octicon-code"></span>&nbsp;&nbsp;
     <a>现在框架的发展，已经到弱化语言的程度，但是我依然认为语言基础是很重要的，尤其是一些触类旁通的思想
     非常值得学习，下面是我java语言学习记录。</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /zh/java
lang: zh
---


<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
                {% assign posts = site.posts | where:"lang", "zh"  %}
                {% for post in posts %}
                {% if post.category=='java' or post.keywords contains 'java' %}
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