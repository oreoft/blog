---
layout: page
title: 搜索
titlebar: 搜索
css: ['blog-page.css']
permalink: /search/
lang: zh
---

<div class="search-container">
    <div class="search-box">
        <input type="text" id="search-input" placeholder="输入关键词搜索文章..." class="form-control">
        <div id="search-results" class="search-results"></div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/simple-jekyll-search@1.10.0/dest/simple-jekyll-search.min.js"></script>
<script>
    (function() {
        // 等待 DOM 加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initSearch);
        } else {
            initSearch();
        }
        
        function initSearch() {
            if (typeof SimpleJekyllSearch === 'undefined') {
                console.error('SimpleJekyllSearch library not loaded');
                return;
            }
            
            SimpleJekyllSearch({
                searchInput: document.getElementById('search-input'),
                resultsContainer: document.getElementById('search-results'),
                json: '/search-zh.json',
                searchResultTemplate: '<div class="search-result-item"><h3><a href="{url}">{title}</a></h3><p class="search-meta">日期: {date}</p><p class="search-excerpt">{excerpt}</p></div>',
                noResultsText: '<div class="search-result-item"><p>没有找到相关文章</p></div>',
                limit: 10,
                fuzzy: false
            });
        }
    })();
</script>

<style>
.search-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}
.search-box {
    margin-bottom: 30px;
}
#search-input {
    width: 100%;
    padding: 12px;
    font-size: 16px;
    border: 2px solid #ddd;
    border-radius: 4px;
    margin-bottom: 20px;
}
#search-input:focus {
    outline: none;
    border-color: #007bff;
}
.search-results {
    margin-top: 20px;
}
.search-result-item {
    padding: 15px;
    margin-bottom: 15px;
    border: 1px solid #eee;
    border-radius: 4px;
    background: #fff;
    transition: box-shadow 0.3s;
}
.search-result-item:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.search-result-item h3 {
    margin: 0 0 10px 0;
    font-size: 18px;
}
.search-result-item h3 a {
    color: #007bff;
    text-decoration: none;
}
.search-result-item h3 a:hover {
    text-decoration: underline;
}
.search-meta {
    color: #999;
    font-size: 14px;
    margin: 5px 0;
}
.search-excerpt {
    color: #666;
    font-size: 14px;
    line-height: 1.6;
    margin: 10px 0 0 0;
}
</style>

