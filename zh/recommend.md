---
layout: page
title: 推荐分享
titlebar: 推荐！推荐！
subtitle: <span class="mega-octicon octicon-git-compare"></span>&nbsp;&nbsp;
     <a>这里是我私藏的一些非常好用，可以提高效率或者达到特殊功能的软件或网站，希望你们可以喜欢。
     <br/>如果你们有更好用的，也一定要分享给我哦。</a><br/>
     <br/>Give people wonderful tools And they'll do wonderful things
     &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
css: ['blog-page.css']
permalink: /zh/recommend
lang: zh
---

<div class="row">

    <div class="col-md-12">
    
        <ul id="posts-list">
                {% assign posts = site.posts | where:"lang", "zh"  %}
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