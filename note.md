## 笔记
### 怕忘记
1. 很多东西都是在config.yml里面配
2. 东西是在_posts里面写
3. pages里面是一些模板，他会生成对应的html，在config里面可以配置映射关系（但是还没搞清内容怎么来）
4. layouts是一些排版格式， 写md需要指明哪一种排版（具体在研究）
5. includes我也没搞明白， 但是改了一些样式，会有变化，貌似是对pages里面写的补充

posts 博客内容
_pages 其他需要生成的网页，如About页
_layouts 网页排版模板
_includes 被模板包含的HTML片段，可在_config.yml中修改位置
assets 辅助资源 css布局 js脚本 图片等
_data 动态数据
_sites 最终生成的静态网页
_config.yml 网站的一些配置信息
index.html 网站的入口


只有md的文件上面格式是2018-03-15-正文内容.md 才会被编译

每个分类的html都做了判断，哪些文件会被收录进这里，可以进html改或者在title的正文加上他判断的条件

default 只有文字，连banner都没有
page 有banner 没有版权和目录
about 有banner 有目录 没有版权
post 有banner  有目录 有版权