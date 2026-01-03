#!/usr/bin/env python3
"""
自动翻译博客文章脚本

### 设计思路
1. **简单直接**：
   - **CI/增量模式**（默认）：通过 `git diff` 检测本次 commit 中 `_posts/` 目录下发生变化的中文文章。只要中文文章有变动（无论是新增还是修改），就强制翻译并覆盖到 `en/_posts/` 下的对应位置。保持中英文内容始终同步。
   - **冷启动/全量模式**（`--all`）：遍历 `_posts/` 下所有中文文章。如果对应的英文文章不存在，则进行翻译补充。用于初始化项目或填补缺失的翻译。

2. **配置**：
   - 依赖环境变量 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。

### 用法
1. **安装依赖**:
   # 必须安装 python-frontmatter，不要安装名为 frontmatter 的包
   pip uninstall frontmatter
   pip install openai pyyaml python-frontmatter

2. **本地运行（全量补全）**:
   export OPENAI_API_KEY="sk-xxxx"
   python .github/scripts/translate_posts.py --all

3. **本地运行（模拟 CI 增量）**:
   # 需要有 git 仓库且有未提交或最近提交的变更
   export OPENAI_API_KEY="sk-xxxx"
   python .github/scripts/translate_posts.py
"""

import os
import sys
import subprocess
import re
from pathlib import Path
from openai import OpenAI

# 尝试导入 frontmatter
try:
    import frontmatter
    # 简单的检查，确保是 python-frontmatter
    if not hasattr(frontmatter, 'load'):
        raise ImportError("Installed 'frontmatter' package seems wrong. Please install 'python-frontmatter'.")
except ImportError as e:
    print(f"Error: {e}")
    print("Please run: pip uninstall frontmatter && pip install python-frontmatter")
    sys.exit(1)

# --- 配置部分 ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL') # 默认 Base URL

if not OPENAI_API_KEY:
    if os.getenv('GITHUB_ACTIONS'):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    else:
        print("Warning: OPENAI_API_KEY not set. Translation will fail.")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
) if OPENAI_API_KEY else None

# --- 核心逻辑 ---

def is_valid_post_path(file_path):
    """
    判断文件路径是否需要处理
    规则：必须在 _posts/数字年份/ 目录下
    例如: 
    - _posts/2021/abc.md -> True
    - _posts/2022/def.md -> True
    - _posts/draft/ghi.md -> False
    - _posts/README.md -> False
    """
    path = Path(file_path)
    # 检查路径中是否包含 _posts
    parts = path.parts
    try:
        posts_index = parts.index('_posts')
        # 检查 _posts 的下一级目录是否是数字（年份）
        if len(parts) > posts_index + 1:
            year_dir = parts[posts_index + 1]
            if year_dir.isdigit() and len(year_dir) == 4:
                return True
    except ValueError:
        pass
    
    return False

def get_changed_files_from_git():
    """
    获取本次提交中新增或修改的中文文章列表
    逻辑：通过 git diff HEAD~1 HEAD 获取变动文件列表
    """
    try:
        # 在 GitHub Actions 中，fetch-depth: 0 保证了有足够的历史
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError:
        print("Warning: Could not get git diff. Returning empty list.")
        return []
    
    changed = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        full_path = os.path.join(os.getcwd(), line)
        
        # 1. 处理 _posts 下的文章
        if line.startswith('_posts/') and line.endswith('.md'):
            # 必须是有效的年份目录
            if not is_valid_post_path(full_path):
                continue
            # 文件必须存在（处理删除的情况）
            if os.path.exists(full_path):
                if is_chinese_post(full_path):
                    changed.append(full_path)
        
        # 2. 处理页面文件：zh/about.md 和 zh/link.md
        elif line in ['zh/about.md', 'zh/link.md']:
            if os.path.exists(full_path):
                if is_chinese_post(full_path):
                    changed.append(full_path)
    
    return changed

def is_chinese_post(file_path):
    """判断是否为中文文章"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            # 显式标记为 zh 或没有标记（默认为中文）
            if post.metadata.get('lang') == 'zh' or post.metadata.get('lang') is None: 
                return True
    except Exception as e:
        print(f"Error checking file language {file_path}: {e}")
    return False

def translate_text(text, model="gpt-5.2"): # 使用更经济的模型，根据需要调整
    """调用 LLM 进行翻译"""
    if not client:
        print("Error: OpenAI client not initialized")
        return None

    prompt = """你是一个专业的英文技术博客翻译助手。请将以下中文技术博客内容翻译成英文。

核心原则：
1. 保持技术术语的准确性。
2. 保持原文的语气和风格（轻松、真实、第一人称）。
3. **严格保持 Markdown 格式不变**（标题、列表、引用、粗体等）。
4. **代码块（``` code ```）内部的内容绝对不要翻译**，保持原样。
5. **流程图/图表定义**（如 mermaid, plantuml）：**请翻译图表中的标签和说明文字**，但保持图表结构语法不变。
6. 图片链接、超链接保持不变。
7. 翻译要自然流畅，符合英文技术博客的写作习惯。

请直接返回翻译后的内容，不要包含任何解释性文字。"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Translation error: {e}")
        return None

def process_post(zh_path, force=False):
    """
    处理单篇文章翻译
    params:
        zh_path: 中文文章路径
        force: 是否强制翻译（True=覆盖，False=仅当英文不存在时翻译）
    """
    try:
        zh_path_obj = Path(zh_path)
        
        # 判断是 _posts 下的文章还是页面文件
        if '_posts' in zh_path_obj.parts:
            # _posts 下的文章：_posts/2021/xxx.md -> en/_posts/2021/xxx.md
            rel_path = zh_path_obj.relative_to(Path(os.getcwd()) / '_posts')
            en_path = Path(os.getcwd()) / 'en' / '_posts' / rel_path
        else:
            # 页面文件：zh/about.md -> en/about.md, zh/link.md -> en/link.md
            if zh_path_obj.name in ['about.md', 'link.md']:
                en_path = Path(os.getcwd()) / 'en' / zh_path_obj.name
            else:
                print(f"Unknown file type: {zh_path}")
                return False
        
        # 策略检查
        if en_path.exists() and not force:
            # print(f"Skip {zh_path}: English version exists (use force to overwrite)")
            return False
            
        print(f"Translating {zh_path} -> {en_path} ...")
        
        # 读取内容
        with open(zh_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            
        # 1. 翻译 Front Matter
        post.metadata['lang'] = 'en'
        
        if 'title' in post.metadata:
            res = translate_text(f"Translate title to English: {post.metadata['title']}")
            if res: post.metadata['title'] = res.strip().strip('"')
        
        if 'titlebar' in post.metadata:
            res = translate_text(f"Translate titlebar to English: {post.metadata['titlebar']}")
            if res: post.metadata['titlebar'] = res.strip().strip('"')
            
        if 'excerpt' in post.metadata:
            res = translate_text(f"Translate excerpt to English: {post.metadata['excerpt']}")
            if res: post.metadata['excerpt'] = res.strip()
        
        # 更新 permalink（如果是页面文件）
        if 'permalink' in post.metadata and '_posts' not in zh_path_obj.parts:
            permalink = post.metadata['permalink']
            if permalink.startswith('/') and not permalink.startswith('/en'):
                post.metadata['permalink'] = '/en' + permalink
            
        # 2. 翻译正文
        if post.content.strip():
            translated_body = translate_text(post.content)
            if not translated_body:
                print(f"Failed to translate content for {zh_path}")
                return False
            post.content = translated_body
            
        # 3. 写入文件
        en_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(en_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            # 写入失败，删除可能创建的不完整文件
            if en_path.exists():
                os.remove(en_path)
            raise e
            
        print(f"✓ Success: {en_path}")
        return True

    except Exception as e:
        print(f"Error processing {zh_path}: {e}")
        return False

def run_batch_mode():
    """冷启动模式：扫描所有中文文章，补全缺失的英文文章"""
    print("=== Running Batch Mode (Fill Missing Translations) ===")
    posts_dir = Path(os.getcwd()) / '_posts'
    count = 0
    
    for root, _, files in os.walk(posts_dir):
        for file in files:
            if file.endswith('.md'):
                full_path = os.path.join(root, file)
                
                # 过滤：只处理 _posts/数字年份/ 下的文件
                if not is_valid_post_path(full_path):
                    continue

                if is_chinese_post(full_path):
                    # force=False 意味着只翻译不存在的
                    if process_post(full_path, force=False):
                        count += 1
    print(f"\nBatch processing complete. Translated {count} new files.")

def run_ci_mode():
    """CI 模式：基于 git diff 强制同步变动的文件"""
    print("=== Running CI Mode (Sync Changed Files) ===")
    changed_files = get_changed_files_from_git()
    
    if not changed_files:
        print("No Chinese posts changed.")
        return

    print(f"Found {len(changed_files)} changed files.")
    count = 0
    for f in changed_files:
        # force=True 意味着只要中文变了，英文必须重写以保持同步
        if process_post(f, force=True):
            count += 1
            
    print(f"\nCI processing complete. Updated {count} files.")

def main():
    # 简单的命令行参数处理
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        run_batch_mode()
    else:
        run_ci_mode()

if __name__ == '__main__':
    main()
