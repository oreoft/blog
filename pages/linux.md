---
layout: page
title: Linux的学习记录
titlebar: Linux快到碗里来
subtitle: <span class="mega-octicon octicon-terminal"></span>&nbsp;&nbsp;
     <a>对终端的黑乎乎的框框有着着魔的热爱，linux学习不是一蹴而就，需要反复的实践积累，
     <br/>下面是我学到的知识和命令积攒记录起来，你愿意和我一起学习吗？</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /linux
---


<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% for post in site.posts %}
                {% if post.category=='linux' or post.keywords contains 'linux' %}
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