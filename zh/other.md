---
layout: page
title: 其 他
titlebar: 乱七八糟
subtitle: <span class="mega-octicon octicon-list-unordered"></span>&nbsp;&nbsp;
     <a >我不知道分类的就会放这里....</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /zh/other
lang: zh
---


<div class="row">

    <div class="col-md-12">
    
        <ul id="posts-list">
                {% assign posts = site.posts | where:"lang", "zh"  %}
                {% for post in posts %}
                {% if post.category=='other' or post.keywords contains 'other' or post.category=='others' or post.keywords contains 'others' %}
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