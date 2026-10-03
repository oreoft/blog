# 中文页面在 /xxx，英文翻译在 /en/xxx。所有生成器跑完之后，给中英文都存在的页面记下对应关系，
# head.html 据此输出 hreflang。只有一种语言的页面（还没翻译的新文章、跳转页等）不输出。
require 'set'

Jekyll::Hooks.register :site, :pre_render do |site|
  docs = site.pages + site.posts.docs
  urls = docs.map(&:url).to_set

  docs.each do |doc|
    url = doc.url
    if url == '/en/' || url.start_with?('/en/')
      zh_url = url.sub(%r{\A/en}, '')
      en_url = url
    else
      zh_url = url
      en_url = "/en#{url}"
    end
    next unless urls.include?(zh_url) && urls.include?(en_url)

    doc.data['hreflang'] = { 'zh' => zh_url, 'en' => en_url }
  end
end
