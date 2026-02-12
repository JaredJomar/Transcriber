# Transcriber UI Output and Icon Adjustments

## TL;DR

> **Quick Summary**: Move the output directory controls from the Settings tab to the Transcribe tab, clear the URL field after any transcription ends, and set the window icon using the existing app icon asset.
>
> **Deliverables**:
> - Output directory input + Browse button located on the Transcribe tab (below URL)
> - URL input auto-clears after success/error/cancel
> - Window icon set (title bar + taskbar)
>
> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential
> **Critical Path**: Task 1 → Task 2 → Task 3

---

## Context

### Original Request
"Mover el ouput from setting to main tab and auto remove url the url input box when transcrition end to not have to remove it manual to paste the next one" + "also put the icon on the ui window".

### Interview Summary
**Key Discussions**:
- Output controls should be moved from Settings to the Main/Transcribe tab and removed from Settings.
- URL input should clear after transcription ends (success, error, or cancel).
- Icon should be set at the window level (title bar + taskbar/dock), no in-app logo.
- Output placement: below the URL input in the Transcribe tab.
- No automated tests; manual verification only.

**Research Findings**:
- UI is built in `app/window.py` in `MainWindow._build_ui()` with `Transcribe` and `Settings` tabs.
- URL input is `self.url_input` in the Transcribe tab; output directory input is `self.output_dir_input` in Settings.
- Completion handler is `MainWindow._on_finished()`; `TranscribeWorker.finished` emits on success/error/cancel (`app/worker.py`).
- App entry point is `main.py`; icon assets exist in `icons/` (e.g., `icons/app_icon.ico`).

### Metis Review
**Identified Gaps** (addressed):
- Ensure output browse button is reconnected after moving controls.
- Confirm manual acceptance criteria for success/error/cancel URL clearing and icon appearance.
- Decide icon file usage: use existing `.ico` asset for Windows consistency.

---

## Work Objectives

### Core Objective
Relocate output directory controls to the Transcribe tab, clear URL input after any transcription completion, and display the app icon on the window.

### Concrete Deliverables
- Output directory input + Browse button moved from Settings tab to Transcribe tab.
- URL input cleared in the completion handler regardless of outcome.
- Window icon set using existing icon asset.

### Definition of Done
- Output controls appear under URL in Transcribe tab and are removed from Settings.
- URL input is empty after completion on success/error/cancel.
- Window icon appears in title bar and taskbar.

### Must Have
- No changes to transcription logic or output file format.
- Settings persistence remains intact for output directory.

### Must NOT Have (Guardrails)
- Do not change theme, styling, or tab labels beyond necessary layout updates.
- Do not add new icon assets; use existing `icons/app_icon.ico`.
- Do not alter worker/pipeline logic beyond URL clearing.

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO
- **User wants tests**: NO
- **Framework**: none
- **QA approach**: Manual verification only

---

## Execution Strategy

### Parallel Execution Waves

Wave 1 (Start Immediately):
├── Task 1: Move output controls to Transcribe tab
└── Task 2: Clear URL input on finish

Wave 2 (After Wave 1):
└── Task 3: Set window icon

Critical Path: Task 1 → Task 2 → Task 3

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 2, 3 | 2 |
| 2 | 1 | 3 | 1 |
| 3 | 2 | None | None |

---

## TODOs

- [ ] 1. Move output directory controls to the Transcribe tab

  **What to do**:
  - Move `self.output_dir_input` and its Browse button from Settings tab to the Transcribe tab settings group.
  - Place the Output row below the URL input (maintain layout spacing).
  - Remove Output row from Settings tab layout.
  - Ensure Browse button is still connected to `_browse_output_dir()`.
  - Keep `self.output_dir_input` persistence via `_load_settings()` / `_save_settings()` unchanged.

  **Must NOT do**:
  - Do not change settings keys or output directory persistence.
  - Do not change tab labels or unrelated controls.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file UI layout change with limited surface area.
  - **Skills**: `frontend-ui-ux`
    - `frontend-ui-ux`: UI layout adjustments in Qt widgets.
  - **Skills Evaluated but Omitted**:
    - `git-master`: no git operations needed in this task.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None

  **References**:
  - `app/window.py` - `MainWindow._build_ui()` contains both Transcribe and Settings tab layouts and current Output controls.
  - `app/window.py` - `self.output_dir_input` and `output_browse` creation currently in Settings tab block.
  - `app/window.py` - `_browse_output_dir()` connects to Browse button.

  **Acceptance Criteria (Manual Verification)**:
  - Output directory input + Browse button appear in Transcribe tab under the URL field.
  - Settings tab no longer shows the Output row.
  - Browse button still opens folder picker and updates the Output field.
  - Output directory value persists after app restart.

- [ ] 2. Clear URL input when transcription ends (success/error/cancel)

  **What to do**:
  - In `MainWindow._on_finished()`, clear `self.url_input` after updating UI state.
  - Ensure URL clears on all completion outcomes (success, error, cancel).

  **Must NOT do**:
  - Do not change completion messaging or logging semantics.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small UI behavior change in a single method.
  - **Skills**: `frontend-ui-ux`
    - `frontend-ui-ux`: UI state interaction in Qt.
  - **Skills Evaluated but Omitted**:
    - `git-master`: no git operations needed in this task.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `app/window.py` - `MainWindow._on_finished()` is the completion handler.
  - `app/worker.py` - `TranscribeWorker.finished` is emitted for success/error/cancel.

  **Acceptance Criteria (Manual Verification)**:
  - Start a transcription and cancel it: URL input is empty once finished.
  - Run a transcription to completion: URL input is empty after completion.
  - Trigger an error (e.g., invalid URL): URL input is empty after error.

- [ ] 3. Set window icon using existing app icon asset

  **What to do**:
  - Set the window icon on `MainWindow` using `icons/app_icon.ico`.
  - Set the QApplication icon in `main.py` for taskbar consistency.

  **Must NOT do**:
  - Do not add new icon files or change icon assets.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small change to window/application setup.
  - **Skills**: `frontend-ui-ux`
    - `frontend-ui-ux`: UI presentation and window configuration.
  - **Skills Evaluated but Omitted**:
    - `git-master`: no git operations needed in this task.

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 1 & 2)
  - **Blocks**: None
  - **Blocked By**: Task 2

  **References**:
  - `app/window.py` - `MainWindow.__init__()` is where window properties are set.
  - `main.py` - `QApplication` is instantiated here.
  - `icons/app_icon.ico` - existing icon file to use.

  **Acceptance Criteria (Manual Verification)**:
  - Window title bar shows the app icon after launch.
  - Taskbar/dock shows the app icon when running.

---

## Commit Strategy

- Commit: NO (not requested)

---

## Success Criteria

### Manual Verification Checklist
- Output controls appear in Transcribe tab (below URL) and are removed from Settings.
- URL field clears after completion for success/error/cancel.
- App icon appears in window title bar and taskbar.
