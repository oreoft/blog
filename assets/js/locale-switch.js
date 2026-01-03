(function() {
  var langs = ['zh', 'en'];
  var defaultLang = 'zh';
  var currentPath = window.location.pathname;
  var currentLang = currentPath.startsWith('/en/') ? 'en' : 'zh';
  
  // 1. 获取用户偏好 (LocalStorage > Browser)
  var preferredLang = localStorage.getItem('user_lang');
  
  // 如果没有手动设置过，且当前是首次访问首页
  if (!preferredLang) {
    var browserLang = navigator.language || navigator.userLanguage;
    preferredLang = browserLang.startsWith('zh') ? 'zh' : 'en';
    
    // 只有在首页才进行自动跳转，避免干扰用户通过直接链接访问文章
    // 或者是当用户偏好与当前语言不一致时，但我们这里保守一点，只处理首页
    if (currentPath === '/' && preferredLang === 'en') {
      window.location.href = '/en/';
    } else if (currentPath === '/en/' && preferredLang === 'zh') {
      window.location.href = '/';
    }
  } else {
    // 如果有偏好设置，且当前在首页，强制跳转到偏好语言
    // 同样只处理首页，避免死循环或干扰深度链接
    if (currentPath === '/' && preferredLang === 'en') {
      window.location.href = '/en/';
    } else if (currentPath === '/en/' && preferredLang === 'zh') {
      window.location.href = '/';
    }
  }
})();

// 语言切换函数
function switchLanguage(targetLang) {
  // 1. 记录偏好
  localStorage.setItem('user_lang', targetLang);
  
  // 2. 计算目标 URL
  var currentPath = window.location.pathname;
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

