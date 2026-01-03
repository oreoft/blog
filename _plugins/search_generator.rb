module Jekyll
  class SearchGenerator < Generator
    safe true
    priority :lowest

    # 简单的 HTML 标签移除方法
    def strip_html(text)
      return '' if text.nil?
      text.to_s.gsub(/<[^>]*>/, '').strip
    end

    def generate(site)
      # 生成中文搜索数据
      zh_posts = site.posts.docs.select { |post| post.data['lang'] == 'zh' }
      zh_search_data = zh_posts.map do |post|
        excerpt_text = post.data['excerpt'] ? strip_html(post.data['excerpt'].to_s) : ''
        content_text = post.content ? strip_html(post.content) : ''
        {
          'title' => post.data['title'] || '',
          'url' => post.url,
          'date' => post.date.strftime('%Y-%m-%d'),
          'excerpt' => excerpt_text[0..200] || '',
          'content' => content_text[0..500] || ''
        }
      end

      # 生成英文搜索数据
      en_posts = site.posts.docs.select { |post| post.data['lang'] == 'en' }
      en_search_data = en_posts.map do |post|
        excerpt_text = post.data['excerpt'] ? strip_html(post.data['excerpt'].to_s) : ''
        content_text = post.content ? strip_html(post.content) : ''
        {
          'title' => post.data['title'] || '',
          'url' => post.url,
          'date' => post.date.strftime('%Y-%m-%d'),
          'excerpt' => excerpt_text[0..200] || '',
          'content' => content_text[0..500] || ''
        }
      end

      # 创建中文搜索 JSON 页面
      zh_search_page = Jekyll::PageWithoutAFile.new(site, site.source, '', 'search-zh.json')
      zh_search_page.data['layout'] = nil
      zh_search_page.data['permalink'] = '/search-zh.json'
      zh_search_page.content = zh_search_data.to_json
      site.pages << zh_search_page

      # 创建英文搜索 JSON 页面
      en_search_page = Jekyll::PageWithoutAFile.new(site, site.source, 'en', 'search-en.json')
      en_search_page.data['layout'] = nil
      en_search_page.data['permalink'] = '/en/search-en.json'
      en_search_page.content = en_search_data.to_json
      site.pages << en_search_page

      Jekyll.logger.info "SearchGenerator: Generated search data for #{zh_posts.size} zh posts and #{en_posts.size} en posts"
    end
  end
end

