---
layout: page
title: design pattern
titlebar: Elegance in the making
subtitle: <span class="mega-octicon octicon-pulse"></span>&nbsp;&nbsp;
     <a>Work for a period of time, the code has also written a lot, sometimes want to optimize some code structure has no idea. Now systematically study the design patterns again, absorb the wisdom of the past, open up their own horizons, so that the code is more elegant and flexible!</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /design
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
                {% if post.category=='design' or post.keywords contains 'design' %}
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