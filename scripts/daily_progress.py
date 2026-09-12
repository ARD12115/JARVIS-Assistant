#!/usr/bin/env python3
"""
Daily Progress Logger for JARVIS Assistant
Generates daily progress markdown from git commits and kanban tasks.
"""

import subprocess
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def run_cmd(cmd: list[str]) -> str:
    """Run command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        return result.stdout.strip()
    except Exception:
        return ""


def get_git_commits(since: str) -> list[dict]:
    """Get git commits since date."""
    cmd = ["git", "log", f"--since={since}", "--pretty=format:%H|%s|%an|%ad", "--date=short"]
    output = run_cmd(cmd)
    commits = []
    for line in output.split('\n'):
        if line:
            parts = line.split('|', 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3]
                })
    return commits


def get_kanban_tasks() -> list[dict]:
    """Get kanban tasks from Hermes."""
    # This would need hermes CLI integration
    # For now, return empty
    return []


def get_file_stats() -> dict:
    """Get lines of code stats."""
    cmd = ["find", "src-python", "src-frontend", "src-tauri", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx", "-o", "-name", "*.rs"]
    files = run_cmd(cmd).split('\n')
    
    total_lines = 0
    total_files = 0
    for f in files:
        if f and os.path.exists(f):
            try:
                with open(f, 'r') as fp:
                    lines = len(fp.readlines())
                    total_lines += lines
                    total_files += 1
            except Exception:
                pass
    
    return {"files": total_files, "lines": total_lines}


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Get data
    commits = get_git_commits(yesterday)
    stats = get_file_stats()
    kanban_tasks = get_kanban_tasks()
    
    # Group commits by type
    features = [c for c in commits if c['message'].startswith('feat:')]
    fixes = [c for c in commits if c['message'].startswith('fix:')]
    refactors = [c for c in commits if c['message'].startswith('refactor:')]
    docs = [c for c in commits if c['message'].startswith('docs:')]
    tests = [c for c in commits if c['message'].startswith('test:')]
    others = [c for c in commits if not any(c['message'].startswith(p) for p in ['feat:', 'fix:', 'refactor:', 'docs:', 'test:'])]
    
    # Generate markdown
    md = f"""# Daily Progress — {today}

## Summary
- **Commits**: {len(commits)}
- **Files**: {stats['files']}
- **Lines of Code**: {stats['lines']}
- **Date**: {today}

## Completed Tasks
"""
    
    if features:
        md += "\n### ✨ Features\n"
        for c in features:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if fixes:
        md += "\n### 🐛 Fixes\n"
        for c in fixes:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if refactors:
        md += "\n### ♻️ Refactors\n"
        for c in refactors:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if docs:
        md += "\n### 📝 Documentation\n"
        for c in docs:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if tests:
        md += "\n### ✅ Tests\n"
        for c in tests:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if others:
        md += "\n### 🔧 Other\n"
        for c in others:
            md += f"- {c['message']} (`{c['hash']}`)\n"
    
    if not commits:
        md += "\n_No commits today._\n"
    
    md += f"""
## Kanban Status
"""
    
    if kanban_tasks:
        for task in kanban_tasks:
            md += f"- **{task.get('title', 'Unknown')}**: {task.get('status', 'unknown')}\n"
    else:
        md += "\n_No kanban data available (run `hermes kanban list` manually)._\n"
    
    md += f"""
## Metrics
- **Backend Latency**: N/A (add monitoring)
- **Test Coverage**: N/A (run `pytest --cov`)
- **Bundle Size**: N/A (run `pnpm tauri build`)

## Next Steps
- [ ] Review today's commits
- [ ] Plan tomorrow's tasks in kanban
- [ ] Update PRD/TRD if architecture changed

---
*Generated automatically by `scripts/daily_progress.py`*
"""
    
    # Write to file
    output_dir = Path(__file__).parent.parent / "docs" / "progress"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{today}.md"
    
    with open(output_file, 'w') as f:
        f.write(md)
    
    print(f"✅ Daily progress written to {output_file}")


if __name__ == "__main__":
    main()