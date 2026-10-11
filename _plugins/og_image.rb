require 'cgi'

# 文章没单独指定 image 时（拿到的是 _config.yml 里的默认图），分享图改用 /api/og 按标题现画一张
DEFAULT_OG_IMAGE = '/assets/images/og-image.jpg'

Jekyll::Hooks.register :posts, :pre_render do |post|
  next unless post.data['image'].nil? || post.data['image'] == DEFAULT_OG_IMAGE
  post.data['image'] = "/api/og?title=#{CGI.escape(post.data['title'].to_s)}"
end
