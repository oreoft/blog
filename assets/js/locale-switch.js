(function() {
  var langs = ['zh', 'en'];
  var defaultLang = 'zh';
  var currentPath = window.location.pathname;
  var currentLang = currentPath.startsWith('/en/') ? 'en' : 'zh';
  
  // 只尊重用户手动切换过的语言偏好。不再按浏览器语言自动跳转：
  // 搜索引擎爬虫用英文环境渲染，自动跳转会让它抓不到中文首页，语言对应关系交给 hreflang。
  var preferredLang = null;
  try {
    preferredLang = localStorage.getItem('user_lang');
  } catch (e) {}

  // 只处理首页，避免死循环或干扰深度链接
  if (currentPath === '/' && preferredLang === 'en') {
    window.location.href = '/en/';
  } else if (currentPath === '/en/' && preferredLang === 'zh') {
    window.location.href = '/';
  }
})();

// 语言切换函数
function switchLanguage(targetLang) {
  // 1. 记录偏好
  localStorage.setItem('user_lang', targetLang);
  
  // 2. 计算目标 URL
  var currentPath = window.location.pathname;
  // /zh/ 是首页的旧地址，按首页处理
  if (currentPath === '/zh/' || currentPath === '/zh') {
    currentPath = '/';
  }
  var newPath = currentPath;
  
  if (targetLang === 'en') {
    // 切换到英文
    if (!currentPath.startsWith('/en/')) {
        // 如果是根路径 /
        if (currentPath === '/') {
            newPath = '/en/';
        } else {
            newPath = '/en' + currentPath;
        }
    }
  } else {
    // 切换到中文
    if (currentPath.startsWith('/en/')) {
        newPath = currentPath.replace('/en/', '/');
    }
  }
  
  // 3. 尝试跳转
  // 这里有一个潜在问题：如果目标语言的文章不存在，会 404
  // 理想情况下应该先 check 一下，但静态博客很难 check
  // 简单策略：直接跳转，让 404 页面处理（或者 404 页面可以引导回首页）
  window.location.href = newPath;
}

