module Jekyll
  class PaginationGenerator < Generator
    safe true
    priority :lowest

    def generate(site)
      begin
        # 从配置获取每页数量，默认6
        per_page = site.config['posts_per_page'] || 6
        
        # 处理中文分页
        zh_posts = site.posts.docs.select { |post| post.data['lang'] == 'zh' }
        zh_posts.sort! { |a, b| b.date <=> a.date }
        zh_total_pages = (zh_posts.size.to_f / per_page).ceil
        
        Jekyll.logger.info "PaginationGenerator: Found #{zh_posts.size} zh posts, will generate #{zh_total_pages} pages"
        
        if zh_total_pages >= 2
          # 读取 index.html 的内容作为模板
          index_path = File.join(site.source, 'index.html')
          if File.exist?(index_path)
            content = File.read(index_path)
            # 移除 front matter
            content = content.sub(/^---\n.*?---\n/m, '')
            
            # 为中文首页生成分页页面
            (2..zh_total_pages).each do |page_num|
              page = Jekyll::PageWithoutAFile.new(site, site.source, "page#{page_num}", 'index.html')
              page.data['layout'] = 'default'
              page.data['menu'] = 'home'
              page.data['css'] = ['index.css', 'sidebar-popular-repo.css']
              page.data['lang'] = 'zh'
              page.data['permalink'] = "/page#{page_num}/"
              page.content = content
              site.pages << page
            end
          end
        end
        
        # 处理英文分页
        en_posts = site.posts.docs.select { |post| post.data['lang'] == 'en' }
        en_posts.sort! { |a, b| b.date <=> a.date }
        en_total_pages = (en_posts.size.to_f / per_page).ceil
        
        Jekyll.logger.info "PaginationGenerator: Found #{en_posts.size} en posts, will generate #{en_total_pages} pages"
        
        if en_total_pages >= 2
          # 读取 en/index.html 的内容作为模板
          en_index_path = File.join(site.source, 'en', 'index.html')
          if File.exist?(en_index_path)
            content = File.read(en_index_path)
            # 移除 front matter
            content = content.sub(/^---\n.*?---\n/m, '')
            
            # 为英文首页生成分页页面
            (2..en_total_pages).each do |page_num|
              page = Jekyll::PageWithoutAFile.new(site, site.source, File.join('en', "page#{page_num}"), 'index.html')
              page.data['layout'] = 'default'
              page.data['menu'] = 'home'
              page.data['css'] = ['index.css', 'sidebar-popular-repo.css']
              page.data['lang'] = 'en'
              page.data['permalink'] = "/en/page#{page_num}/"
              page.content = content
              site.pages << page
            end
          end
        end
      rescue => e
        Jekyll.logger.error "PaginationGenerator error: #{e.message}"
        Jekyll.logger.error e.backtrace.join("\n")
      end
    end
  end
end

