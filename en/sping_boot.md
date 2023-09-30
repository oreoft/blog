---
layout: page
title: Spring Boot Learning Record
titlebar: spring_boot
subtitle: <span class="mega-octicon octicon-eye"></span>&nbsp;&nbsp;
     <a>Sring Boot is currently the hottest framework for the java platform, the following are all my learning records, I hope to help you, together to make progress.</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /spring_boot
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
                {% if post.category=='springboot' or post.keywords contains 'spring' %}
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