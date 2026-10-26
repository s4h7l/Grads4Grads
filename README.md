# Grads4Grads

Grads4Grads is a static study and practice site for Semester 1 students. It brings published notes, subject Q&A, practice questions, and quizzes into one browser-based space.

**Live site:** https://grads4grads.vercel.app

## What it includes

- Six Semester 1 subject cards. Semester 1 is open; later semesters are shown as locked until their content is ready.
- Published notes and reference links, Q&A, practice MCQs, and a randomized 10-question Grand Quiz.
- PDF resources and 289 rendered PDF page images for the included study materials.
- An announcements panel and light/dark themes.
- No student accounts or server-side quiz database. Quiz results and read/unread announcement state stay in the visitor's browser.

## Project structure

- **content/** — source JSON used by the publisher.
- **site/** — the static website served by Vercel.
  - **index.html**, **subjects.html** — student-facing pages.
  - **assets/** — styles, scripts, and the site mark.
  - **data/published.json** — content consumed by the site.
  - **resources/** — original PDFs.
  - **pages/** — page images used by the notes reader.
- **publish.py** — owner-side content publishing commands.
- **source_questions.py** — extraction helpers used by the publisher.
- **PREVIEW_WINDOWS.bat**, **PREVIEW_MAC_LINUX.sh** — local preview launchers.

Keep the files under **site/assets/**, **site/data/**, **site/pages/**, and **site/resources/** together. The site uses their existing relative paths.

## Preview locally

### Windows

1. Install Python 3.
2. Double-click **PREVIEW_WINDOWS.bat**.
3. Open http://127.0.0.1:8000/ if the browser does not open automatically.

### macOS or Linux

From this folder, run:

    sh START_LECTURA_MAC_LINUX.sh

Then open http://127.0.0.1:8000/. The launcher filename retains its original name for compatibility.

## Update published content

Install the publisher dependencies:

    python -m pip install -r requirements.txt

Examples:

    python publish.py add-file --subject PEA101 --file "C:\Notes\Lecture1.pdf" --title "Lecture 1"
    python publish.py add-link --subject PEA101 --title "Reference notes" --url "https://example.com/notes"
    python publish.py add-qa --subject PEA101 --question "What is a constraint?" --answer "A limit a solution must satisfy."
    python publish.py announce --title "New resource" --message "A new set of notes is available." --subject PEA101
    python publish.py publish

The optional --ai publishing mode reads OPENAI_API_KEY from the publisher's local environment. Keep keys out of source files and never place them in the public site/ directory.

## Deploy

Deploy the contents of site/ as the static website through the existing Vercel project. Preview changes locally before deploying. This repository is separate from the current production deployment and is not configured to deploy automatically.

## Compatibility note

Some helper filenames, DOM IDs, and browser storage keys still contain LECTURA. They remain unchanged so existing scripts, page paths, and saved browser preferences continue to work. The visible project and site branding is Grads4Grads.
