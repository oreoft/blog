Jekyll::Hooks.register [:posts, :pages, :documents], :post_render do |doc|
  # 获取配置
  config = doc.site.config['oss_optimization']
  
  # 如果配置开启且有域名和参数
  if config && config['enable'] && config['domain'] && config['params']
    domain = config['domain']
    params = config['params']
    
    # 正则匹配 src="..." 中的链接
    # 逻辑：查找包含指定域名的 URL
    doc.output.gsub!(/(src=["'])(https?:\/\/#{Regexp.escape(domain)}[^\s"']+)(["'])/) do |match|
      prefix = $1
      url = $2
      suffix = $3
      
      # 检查 URL 是否已经包含了 x-oss-process 参数（防止重复添加）
      if url.include?('x-oss-process')
        match
      else
        # 判断是用 ? 还是 & 连接
        separator = url.include?('?') ? '&' : '?'
        "#{prefix}#{url}#{separator}#{params}#{suffix}"
      end
    end
  end
end

