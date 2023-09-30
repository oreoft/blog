---
layout: page
title: Recommended Sharing
titlebar: Recommended! Recommended!
subtitle: <span class="mega-octicon octicon-git-compare"></span>&nbsp;&nbsp;
     <a>Here are some of my private stash of very good software or websites that can be used to improve efficiency or achieve special functions, I hope you can enjoy them.
     <br/>If you guys have one that works better, be sure to share it with me too!</a><br/>
     <br/>Give people wonderful tools And they'll do wonderful things
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /recommend
lang: en
---

<div class="row">

    <div class="col-md-12">
    
        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
            {% for post in posts %}
                {% if post.category=='recommend' or post.keywords contains 'recommend' %}
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