# 将 en/_posts 下的文件也加载到 posts collection 中
module Jekyll
  Hooks.register :site, :after_init do |site|
    # 获取 en/_posts 目录下的所有 markdown 文件
    en_posts_dir = File.join(site.source, 'en', '_posts')
    next unless Dir.exist?(en_posts_dir)

    # 遍历所有文件
    Dir.glob(File.join(en_posts_dir, '**', '*.md')).each do |file_path|
      begin
        # 创建相对路径（相对于 site.source）
        relative_path = file_path.sub(site.source + '/', '')
        
        # 创建 Document 对象
        doc = Document.new(file_path, {
          site: site,
          collection: site.collections['posts']
        })
        
        # 读取 front matter 和内容
        doc.read
        
        # 设置 permalink（如果需要）
        if doc.data['permalink'].nil?
          # 根据文件路径生成 permalink
          date_match = File.basename(file_path).match(/(\d{4})-(\d{2})-(\d{2})-(.+)\.md/)
          if date_match
            year, month, day, slug = date_match[1], date_match[2], date_match[3], date_match[4]
            doc.data['permalink'] = "/en/#{year}/#{month}/#{day}/#{slug}/"
          end
        end
        
        # 添加到 posts collection
        site.collections['posts'].docs << doc
      rescue => e
        Jekyll.logger.warn "Error loading en post #{file_path}: #{e.message}"
      end
    end
  end
end
