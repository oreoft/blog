---
layout: page
title: Fundamentals of Electricity
titlebar: A little bit of electrical knowledge.
subtitle: <span class="mega-octicon octicon-tools"></span>&nbsp;&nbsp;
     <a>Day after day listening to B station Nambashi gambling god's laptop repair guy's green wave electric dragon, curious about this piece, so will look for information to learn.
     <br/>There may be some authorized learning articles reprinted here</a><br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
css: ['blog-page.css']
permalink: /ee
lang: en
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% assign posts = site.posts | where:"lang", "en"  %}
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