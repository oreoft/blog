module Jekyll
  module I18nFilter
    # 用法: {{ 'site.title' | t }}
    # 自动根据 page.lang 获取翻译
    # 如果找不到，返回 key 本身
    def t(key)
      lang = @context.registers[:page]['lang'] || 'zh'
      translations = @context.registers[:site].data['i18n']
      
      return key unless translations && translations[lang]
      
      # 支持点号嵌套，如 'site.title'
      result = translations[lang]
      key.split('.').each do |k|
        result = result[k] if result
      end
      
      result || key
    end
  end
end

Liquid::Template.register_filter(Jekyll::I18nFilter)

