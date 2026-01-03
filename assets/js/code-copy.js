(function() {
    // 为所有代码块添加复制按钮
    function addCopyButtons() {
        // 查找所有代码块容器
        const codeBlocks = document.querySelectorAll('pre code, pre');
        
        codeBlocks.forEach(function(block) {
            // 跳过已经有复制按钮的代码块
            if (block.parentElement.querySelector('.code-copy-btn')) {
                return;
            }
            
            // 创建复制按钮
            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-copy-btn';
            copyBtn.innerHTML = '<span class="copy-icon">📋</span><span class="copy-text">复制</span>';
            copyBtn.setAttribute('aria-label', '复制代码');
            copyBtn.setAttribute('title', '复制代码');
            
            // 获取代码内容
            const code = block.textContent || block.innerText;
            
            // 添加点击事件
            copyBtn.addEventListener('click', function() {
                // 使用现代 Clipboard API
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(code).then(function() {
                        // 成功反馈
                        copyBtn.innerHTML = '<span class="copy-icon">✓</span><span class="copy-text">已复制</span>';
                        copyBtn.classList.add('copied');
                        setTimeout(function() {
                            copyBtn.innerHTML = '<span class="copy-icon">📋</span><span class="copy-text">复制</span>';
                            copyBtn.classList.remove('copied');
                        }, 2000);
                    }).catch(function(err) {
                        console.error('复制失败:', err);
                        fallbackCopy(code, copyBtn);
                    });
                } else {
                    // 降级方案
                    fallbackCopy(code, copyBtn);
                }
            });
            
            // 将按钮添加到代码块容器
            const pre = block.tagName === 'PRE' ? block : block.parentElement;
            if (pre) {
                pre.style.position = 'relative';
                pre.appendChild(copyBtn);
            }
        });
    }
    
    // 降级复制方案
    function fallbackCopy(text, btn) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            btn.innerHTML = '<span class="copy-icon">✓</span><span class="copy-text">已复制</span>';
            btn.classList.add('copied');
            setTimeout(function() {
                btn.innerHTML = '<span class="copy-icon">📋</span><span class="copy-text">复制</span>';
                btn.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('复制失败:', err);
            btn.innerHTML = '<span class="copy-icon">✗</span><span class="copy-text">失败</span>';
            setTimeout(function() {
                btn.innerHTML = '<span class="copy-icon">📋</span><span class="copy-text">复制</span>';
            }, 2000);
        }
        document.body.removeChild(textarea);
    }
    
    // 页面加载完成后添加复制按钮
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addCopyButtons);
    } else {
        addCopyButtons();
    }
    
    // 如果内容动态加载，可以监听 DOM 变化
    if (window.MutationObserver) {
        const observer = new MutationObserver(function(mutations) {
            let shouldAdd = false;
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    shouldAdd = true;
                }
            });
            if (shouldAdd) {
                addCopyButtons();
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
})();

