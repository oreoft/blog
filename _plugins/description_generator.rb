# 给没写 description 的文章和页面生成一段纯文本描述，供 <meta name="description"> 和 jekyll-seo-tag 使用。
# 文章优先用 front matter 里的 excerpt；没写 excerpt 的，自动摘要只会拿到"## 前言"这个标题，
# 所以改为取正文去掉第一个标题后的前 150 个字。页面用 subtitle，再没有就用站点描述。
module Jekyll
  module DescriptionGenerator
    MAX_LENGTH = 150

    def self.plain(html)
      text = html.to_s.gsub(/<script.*?<\/script>|<style.*?<\/style>/m, ' ')
      text = text.gsub(/<[^>]+>/, ' ')
      text = CGI.unescapeHTML(text.gsub(/&nbsp;/i, ' '))
      text.gsub(/[[:space:]\u00A0]+/, ' ').strip
    end

    def self.truncate(text)
      text.length > MAX_LENGTH ? "#{text[0, MAX_LENGTH]}…" : text
    end

    def self.site_description(doc)
      lang = doc.data['lang'] || 'zh'
      doc.site.data.dig('i18n', lang, 'site', 'description')
    end

    def self.generate(doc)
      return unless doc.data['description'].to_s.strip.empty?

      excerpt = doc.data['excerpt']
      desc =
        if excerpt.is_a?(String) && !excerpt.strip.empty?
          plain(excerpt)
        elsif doc.respond_to?(:collection) && doc.collection&.label == 'posts'
          plain(doc.content.to_s.sub(/\A\s*<h[1-6][^>]*>.*?<\/h[1-6]>/m, ''))
        elsif doc.data['subtitle']
          plain(doc.data['subtitle'])
        end
      desc = site_description(doc) if desc.to_s.empty?
      doc.data['description'] = truncate(desc) unless desc.to_s.empty?
    end
  end
end

# 文章要用转换后的 HTML，所以挂在 post_convert；文章的 page 变量是实时读取 data 的。
Jekyll::Hooks.register :documents, :post_convert do |doc|
  Jekyll::DescriptionGenerator.generate(doc)
end

# 页面的 page 变量在渲染前就生成好了，只能在 pre_render 里同时写回 payload。
Jekyll::Hooks.register :pages, :pre_render do |page, payload|
  Jekyll::DescriptionGenerator.generate(page)
  payload['page']['description'] = page.data['description'] if page.data['description']
end
