---
layout: page
title: 计算机网络
titlebar: 计网
subtitle: <span class="mega-octicon octicon-pulse"></span>&nbsp;&nbsp;
     <a>从408开始，我对计算机网络有蜜汁热爱，虽然写业务代码不需要知道计网知识，可是我们生活当中随时随地都在接触网络，你们难道不好奇吗~</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /cn
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% for post in site.posts %}
                {% if post.category=='cn' or post.keywords contains 'cn' %}
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