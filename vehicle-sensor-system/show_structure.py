import os
from pathlib import Path

EXCLUDE_DIRS = {'node_modules', '.git', '__pycache__', '.vscode', '.idea',
                'dist', 'build', '.venv', 'venv', '.pytest_cache', 'logs'}
EXCLUDE_FILES_SUFFIX = {'.pyc', '.log', '.db-journal'}
EXCLUDE_FILES_NAME = {'package-lock.json'}


def should_exclude_file(name):
    if name in EXCLUDE_FILES_NAME:
        return True
    for suffix in EXCLUDE_FILES_SUFFIX:
        if name.endswith(suffix):
            return True
    return False


def format_size(size):
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    else:
        return f"{size / 1024 / 1024:.1f}MB"


def print_tree(path, prefix=""):
    path = Path(path)
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
    except PermissionError:
        return

    items = [i for i in items if not (i.is_dir() and i.name in EXCLUDE_DIRS)
             and not (i.is_file() and should_exclude_file(i.name))]

    for i, item in enumerate(items):
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        if item.is_dir():
            print(f"{prefix}{connector}{item.name}/")
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(item, new_prefix)
        else:
            size = format_size(item.stat().st_size)
            print(f"{prefix}{connector}{item.name}  ({size})")


def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0


def analyze_python_file(filepath):
    """分析 Python 文件中的类和函数数量"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        classes = content.count('\nclass ') + (1 if content.startswith('class ') else 0)
        functions = content.count('\ndef ') + (1 if content.startswith('def ') else 0)
        return classes, functions
    except:
        return 0, 0


def collect_stats(root):
    stats = {'py': [], 'vue': [], 'js': []}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fname.endswith('.py'):
                stats['py'].append(fpath)
            elif fname.endswith('.vue'):
                stats['vue'].append(fpath)
            elif fname.endswith('.js') and 'node_modules' not in str(fpath) and 'dist' not in str(fpath):
                stats['js'].append(fpath)
    return stats


if __name__ == "__main__":
    root = Path(".").resolve()
    print(f"\n📁 项目工程结构：{root.name}/\n")
    print(f"{root.name}/")
    print_tree(root)

    print("\n" + "=" * 60)
    print("📊 代码统计")
    print("=" * 60)

    stats = collect_stats(root)

    total_lines = 0
    for lang, files in stats.items():
        lines = sum(count_lines(f) for f in files)
        total_lines += lines
        print(f"{lang.upper():6s} 文件: {len(files):3d} 个，共 {lines:5d} 行")
    print(f"{'总计':6s}        {sum(len(f) for f in stats.values()):3d} 个，共 {total_lines:5d} 行")

    print("\n" + "=" * 60)
    print("🐍 Python 模块详情（核心后端代码）")
    print("=" * 60)
    for pyfile in sorted(stats['py']):
        rel_path = pyfile.relative_to(root)
        lines = count_lines(pyfile)
        classes, functions = analyze_python_file(pyfile)
        print(f"  {str(rel_path):45s} {lines:4d}行  类:{classes}  函数:{functions}")

    print()