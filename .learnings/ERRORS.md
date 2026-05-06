## [ERR-20260505-001] python_command_unavailable

**Logged**: 2026-05-05T16:10:00+08:00
**Priority**: medium
**Status**: pending
**Area**: infra

### Summary
`python.exe` may be present but inaccessible in this Codex desktop workspace, so verification should first locate an available runtime.

### Error
```text
程序“python.exe”无法运行: 系统无法访问此文件。
```

### Context
- Command attempted: `python -m compileall backend\app backend\dev_server.py`
- Workspace: `D:\code\Projects\识谱ai`
- Shell: PowerShell

### Suggested Fix
Use `load_workspace_dependencies`, `py`, or a project virtualenv path before assuming `python` is runnable.

### Metadata
- Reproducible: unknown
- Related Files: backend/app/services/omr.py

---

## [ERR-20260505-002] powershell_heredoc_not_supported

**Logged**: 2026-05-05T16:14:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
Bash heredoc syntax cannot be used directly in PowerShell commands.

### Error
```text
重定向运算符后面缺少文件规范。
“<”运算符是为将来使用而保留的。
```

### Context
- Command attempted: `python - <<'PY' ... PY`
- Shell: PowerShell

### Suggested Fix
Use PowerShell here-strings piped to Python: `@' ... '@ | python -`, or run a `.py` file.

### Metadata
- Reproducible: yes
- Related Files: backend/app/services/omr.py

---

## [ERR-20260505-003] next_build_spawn_eperm

**Logged**: 2026-05-05T16:14:00+08:00
**Priority**: medium
**Status**: pending
**Area**: frontend

### Summary
`next build` can fail in this sandbox with `spawn EPERM` even before reporting TypeScript or lint issues.

### Error
```text
Build error occurred
[Error: spawn EPERM] { errno: -4048, code: 'EPERM', syscall: 'spawn' }
```

### Context
- Command attempted: `cmd /c "cd frontend && npm run build"`
- Project uses Next.js 15.5.15

### Suggested Fix
Use `npx tsc --noEmit` for a static TypeScript check when Next's build worker cannot spawn in the sandbox.

### Metadata
- Reproducible: unknown
- Related Files: frontend/package.json

---

## [ERR-20260505-004] bundled_python_temp_permission

**Logged**: 2026-05-05T16:20:00+08:00
**Priority**: low
**Status**: pending
**Area**: infra

### Summary
Bundled Python may not be able to write to its default `%TEMP%` path from the sandbox.

### Error
```text
PermissionError: [Errno 13] Permission denied: 'C:\\Users\\RuilinLi\\AppData\\Local\\Temp\\...'
```

### Context
- Runtime: bundled Codex Python
- Operation attempted: `tempfile.TemporaryDirectory()`

### Suggested Fix
Create temporary test folders under the workspace writable root instead of relying on the default temp directory.

### Metadata
- Reproducible: unknown
- Related Files: backend/app/services/omr.py

---
