#!/usr/bin/env python3
"""
自动翻译博客文章脚本

### 设计思路
1. **模式支持**：
   - **CI/增量模式**（默认）：通过 `git diff` 检测变动的中文文章/页面，翻译并同步到 `en/` 对应位置。
   - **全量补全模式**（`--all`）：遍历所有中文文章与页面，仅补全缺失的英文文件，绝不覆盖已有翻译。
   - **指定文件模式**：直接传入一个或多个文件路径进行翻译（若英文文件已存在则跳过）。

2. **配置**：
   - 依赖环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`（可选）和 `OPENAI_MODEL`（可选，默认 gpt-5.4）。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI

# 尝试导入 frontmatter
try:
    import frontmatter
    # 确保是 python-frontmatter
    if not hasattr(frontmatter, 'load'):
        raise ImportError("Installed 'frontmatter' package seems wrong. Please install 'python-frontmatter'.")
except ImportError as e:
    print(f"Error: {e}")
    print("Please run: pip uninstall -y frontmatter && pip install python-frontmatter")
    sys.exit(1)

# --- 根目录定位 ---
def get_repo_root() -> Path:
    """获取 Git 仓库根目录，确保在任意子目录下执行脚本均能正常工作"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        root = Path(result.stdout.strip())
        if root.exists():
            return root
    except Exception:
        pass

    # 脚本默认位于 .github/scripts/ 下，向上查找两级即为根目录
    script_root = Path(__file__).resolve().parent.parent.parent
    if (script_root / '_posts').exists() or (script_root / '_config.yml').exists():
        return script_root

    return Path.cwd()

REPO_ROOT = get_repo_root()

# --- 配置部分 ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.4')

if not OPENAI_API_KEY:
    if os.getenv('GITHUB_ACTIONS'):
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    else:
        print("Warning: OPENAI_API_KEY not set. Translation will fail if API is called.")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
) if OPENAI_API_KEY else None


# --- 辅助逻辑 ---

def is_valid_post_path(file_path):
    """
    判断文件路径是否为合法的年份博客文章
    规则：必须在 _posts/数字年份/ 目录下且为 .md 文件
    例如:
    - _posts/2021/abc.md -> True
    - _posts/2026/def.md -> True
    - _posts/待完成/ghi.md -> False
    - _posts/README.md -> False
    """
    path = Path(file_path).resolve()
    try:
        rel = path.relative_to(REPO_ROOT / '_posts')
        parts = rel.parts
        if len(parts) >= 2 and parts[0].isdigit() and len(parts[0]) == 4 and path.suffix == '.md':
            return True
    except ValueError:
        pass

    return False


def is_valid_page_path(file_path):
    """
    判断文件路径是否为 zh/ 目录下的页面文件
    例如:
    - zh/about.md -> True
    - zh/link.md -> True
    - zh/patriotic.md -> True
    """
    path = Path(file_path).resolve()
    try:
        path.relative_to(REPO_ROOT / 'zh')
        if path.suffix == '.md':
            return True
    except ValueError:
        pass

    return False


def get_target_en_path(zh_path) -> Path:
    """根据中文文件路径计算对应的英文目标文件路径"""
    path = Path(zh_path).resolve()

    # 1. 如果在 _posts/ 下：_posts/2026/xxx.md -> en/_posts/2026/xxx.md
    try:
        rel = path.relative_to(REPO_ROOT / '_posts')
        return REPO_ROOT / 'en' / '_posts' / rel
    except ValueError:
        pass

    # 2. 如果在 zh/ 下：zh/about.md -> en/about.md
    try:
        rel = path.relative_to(REPO_ROOT / 'zh')
        return REPO_ROOT / 'en' / rel
    except ValueError:
        pass

    return None


def is_chinese_post(file_path):
    """判断是否为中文文章/页面"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            # 显式标记为 zh 或没有标记（默认为中文）
            lang = post.metadata.get('lang')
            if lang == 'zh' or lang is None:
                return True
    except Exception as e:
        print(f"Error checking file language {file_path}: {e}")
    return False


def translate_text(text, model=None):
    """调用 LLM 进行翻译"""
    if not client:
        print("Error: OpenAI client not initialized")
        return None

    if model is None:
        model = OPENAI_MODEL

    prompt = """你是一个专业的英文技术博客翻译助手。请将以下中文技术博客内容翻译成英文。

核心原则：
1. 保持技术术语的准确性。
2. 保持原文的语气和风格（轻松、真实、第一人称）。
3. **严格保持 Markdown 格式不变**（标题、列表、引用、粗体等）。
4. **代码块（``` code ```）内部的内容绝对不要翻译**，保持原样。
5. **流程图/图表定义**（如 mermaid, plantuml）：**请翻译图表中的标签和说明文字**，但保持图表结构语法不变。
6. 图片链接、超链接保持不变。
7. **Jekyll / Liquid 模板标签（如 `{% ... %}` 和 `{{ ... }}`）必须严格保持原样，不要翻译或修改内部语法**。
8. 翻译要自然流畅，符合英文技术博客的写作习惯。

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
    处理单篇文章/页面翻译
    params:
        zh_path: 中文文章路径
        force: 是否强制更新已有英文文件（CI 模式修改中文文章时为 True，全量补全模式为 False，保证已有翻译不被覆盖）
    """
    try:
        zh_path_obj = Path(zh_path).resolve()
        if not zh_path_obj.exists():
            print(f"File not found: {zh_path}")
            return False

        en_path = get_target_en_path(zh_path_obj)
        if en_path is None:
            print(f"Skipping {zh_path}: file is neither in _posts/ nor in zh/")
            return False

        # 如果英文版已存在且非 force（例如 --all 全量补全时），安全跳过
        if en_path.exists() and not force:
            return False

        rel_zh = zh_path_obj.relative_to(REPO_ROOT) if zh_path_obj.is_relative_to(REPO_ROOT) else zh_path_obj
        rel_en = en_path.relative_to(REPO_ROOT) if en_path.is_relative_to(REPO_ROOT) else en_path
        print(f"Translating {rel_zh} -> {rel_en} ...")

        # 读取内容
        with open(zh_path_obj, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        # 1. 翻译 Front Matter
        post.metadata['lang'] = 'en'

        if 'title' in post.metadata and isinstance(post.metadata['title'], str) and post.metadata['title'].strip():
            res = translate_text(f"Translate title to English: {post.metadata['title']}")
            if res:
                post.metadata['title'] = res.strip().strip('"').strip("'")

        if 'titlebar' in post.metadata and isinstance(post.metadata['titlebar'], str) and post.metadata['titlebar'].strip():
            res = translate_text(f"Translate titlebar to English: {post.metadata['titlebar']}")
            if res:
                post.metadata['titlebar'] = res.strip().strip('"').strip("'")

        if 'excerpt' in post.metadata and isinstance(post.metadata['excerpt'], str) and post.metadata['excerpt'].strip():
            res = translate_text(f"Translate excerpt to English: {post.metadata['excerpt']}")
            if res:
                post.metadata['excerpt'] = res.strip()

        # 更新 permalink（如果是 zh/ 页面文件）
        try:
            zh_path_obj.relative_to(REPO_ROOT / 'zh')
            if 'permalink' in post.metadata and isinstance(post.metadata['permalink'], str):
                permalink = post.metadata['permalink']
                if permalink.startswith('/') and not permalink.startswith('/en'):
                    post.metadata['permalink'] = '/en' + permalink
        except ValueError:
            pass

        # 2. 翻译正文
        if post.content.strip():
            if post.content.strip() == '{% include blog-page.html %}':
                translated_body = post.content
            else:
                translated_body = translate_text(post.content)
                if not translated_body:
                    print(f"Failed to translate content for {zh_path_obj}")
                    return False
            post.content = translated_body

        # 3. 写入文件
        en_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(en_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            if en_path.exists():
                os.remove(en_path)
            raise e

        print(f"✓ Success: {rel_en}")
        return True

    except Exception as e:
        print(f"Error processing {zh_path}: {e}")
        return False


def get_changed_files_from_git():
    """
    获取提交/变更中新增或修改的中文文章与页面列表
    """
    diff_commands = [
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        ['git', 'diff', '--name-only', 'HEAD'],
        ['git', 'diff', '--name-only', '--cached']
    ]

    raw_files = []
    for cmd in diff_commands:
        try:
            result = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()
            if output:
                raw_files = output.split('\n')
                break
        except subprocess.CalledProcessError:
            continue

    changed = []
    for line in raw_files:
        line = line.strip()
        if not line:
            continue

        full_path = REPO_ROOT / line

        # 1. 处理 _posts 下的文章
        if line.startswith('_posts/') and line.endswith('.md'):
            if not is_valid_post_path(full_path):
                continue
            if full_path.exists() and is_chinese_post(full_path):
                changed.append(full_path)

        # 2. 处理 zh/ 下的页面文件
        elif line.startswith('zh/') and line.endswith('.md'):
            if full_path.exists() and is_chinese_post(full_path):
                changed.append(full_path)

    return changed


def run_batch_mode():
    """
    全量扫描补全模式：扫描所有中文文章与页面，仅补全缺失的英文翻译（绝不覆盖已有文件）
    """
    print("=== Running Batch Mode (Fill Missing Translations) ===")

    count = 0
    total_scanned = 0

    # 1. 扫描 _posts 目录
    posts_dir = REPO_ROOT / '_posts'
    if posts_dir.exists():
        for root, _, files in os.walk(posts_dir):
            for file in sorted(files):
                if file.endswith('.md'):
                    full_path = Path(root) / file
                    if not is_valid_post_path(full_path):
                        continue
                    if is_chinese_post(full_path):
                        total_scanned += 1
                        if process_post(full_path, force=False):
                            count += 1

    # 2. 扫描 zh 目录
    zh_dir = REPO_ROOT / 'zh'
    if zh_dir.exists():
        for root, _, files in os.walk(zh_dir):
            for file in sorted(files):
                if file.endswith('.md'):
                    full_path = Path(root) / file
                    if is_chinese_post(full_path):
                        total_scanned += 1
                        if process_post(full_path, force=False):
                            count += 1

    print(f"\nBatch processing complete. Scanned {total_scanned} Chinese files, translated {count} missing files.")


def run_ci_mode():
    """CI 增量模式：基于 git diff 同步变动的中文文件"""
    print("=== Running CI Mode (Sync Changed Files) ===")
    changed_files = get_changed_files_from_git()

    if not changed_files:
        print("No changed Chinese posts or pages found in git diff.")
        print("Tip: Use '--all' to scan and fill all missing translations.")
        return

    print(f"Found {len(changed_files)} changed file(s).")
    count = 0
    for f in changed_files:
        if process_post(f, force=True):
            count += 1

    print(f"\nCI processing complete. Updated {count} file(s).")


def main():
    parser = argparse.ArgumentParser(description="自动翻译博客文章脚本")
    parser.add_argument(
        '--all',
        action='store_true',
        help='全量补全模式：扫描所有中文文章/页面，仅翻译缺失的英文文件'
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='指定翻译的文件路径（可选）'
    )

    args = parser.parse_args()

    # 1. 如果指定了具体文件
    if args.files:
        print("=== Processing Specified Files ===")
        count = 0
        for f in args.files:
            file_path = Path(f).resolve()
            if process_post(file_path, force=False):
                count += 1
        print(f"\nProcessed {len(args.files)} files, translated {count} files.")
    # 2. 全量补全模式 (--all)
    elif args.all:
        run_batch_mode()
    # 3. 默认 CI 增量模式
    else:
        run_ci_mode()


if __name__ == '__main__':
    main()
