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
   pip install openai pyyaml frontmatter python-frontmatter

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
import frontmatter
from pathlib import Path
from openai import OpenAI

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
            
        # 1. 必须是 _posts 下的 markdown 文件
        if line.startswith('_posts/') and line.endswith('.md'):
            full_path = os.path.join(os.getcwd(), line)
            # 2. 文件必须存在（处理删除的情况）
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
        # 计算相对路径: _posts/2021/xxx.md -> 2021/xxx.md
        rel_path = zh_path_obj.relative_to(Path(os.getcwd()) / '_posts')
        # 构造英文路径: en/_posts/2021/xxx.md
        en_path = Path(os.getcwd()) / 'en' / '_posts' / rel_path
        
        # 策略检查
        if en_path.exists() and not force:
            print(f"Skip {zh_path}: English version exists (use force to overwrite)")
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
            
        if 'excerpt' in post.metadata:
            res = translate_text(f"Translate excerpt to English: {post.metadata['excerpt']}")
            if res: post.metadata['excerpt'] = res.strip()
            
        # 2. 翻译正文
        if post.content.strip():
            translated_body = translate_text(post.content)
            if not translated_body:
                print(f"Failed to translate content for {zh_path}")
                return False
            post.content = translated_body
            
        # 3. 写入文件
        en_path.parent.mkdir(parents=True, exist_ok=True)
        with open(en_path, 'w', encoding='utf-8') as f:
            frontmatter.dump(post, f)
            
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
