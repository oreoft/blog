---
layout: page
title: Computer Network
titlebar: Computer Network
subtitle: <span class="mega-octicon octicon-pulse"></span>&nbsp;&nbsp;
     <a>Since 408, I have had a honeyed love for computer networks. Although you don't need to know about networks to write business code, we are in contact with networks all the time in our lives, so aren't you curious?</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /cn
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
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