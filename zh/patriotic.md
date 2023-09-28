---
layout: page
title: 爱国强国专区
titlebar: 紧密团结在以习近平同志为核心的党中央周围，奋力夺取新时代中国特色社会主义伟大胜利
subtitle: <span class="mega-octicon octicon-thumbsup"></span>&nbsp;&nbsp;
     <a>紧密团结在以习近平同志为核心的党中央周围，奋力夺取新时代中国特色社会主义伟大胜利<br/>
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /zh/patriotic
lang: zh
---

<div class="row">

    <div class="col-md-12">

        <ul id="posts-list">
            {% for post in site.posts %}
                {% if post.category=='patriotic' or post.keywords contains 'patriotic' %}
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