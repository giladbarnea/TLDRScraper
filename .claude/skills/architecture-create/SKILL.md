---
name: architecture-create
description: Create ARCHITECTURE.md document
last_updated: 2026-01-22 12:02, 42883d1
---
# Create an ARCHITECTURE.md File

## Purpose
The overall purpose of this task is twofold:
1. Precisely map the end-to-end call graph for each feature the project provides.
2. Build a crisp state machine that captures each feature’s flow.

## Strategy
Work in a layered approach. Like an oil painter, treat the codebase as the canvas and your task as the drawing. Make multiple passes over the codebase to cultivate a deep understanding of it:

- Start by getting a sense of the overall structure and how the pieces fit together
- Add detail gradually, pass by pass
- Refine the whole system together instead of finishing one part completely before moving on
- Block in the broad areas first, then build up layers of detail across the entire codebase

The end result should be a sharp and precise ARCHITECTURE.md with a clear specification of available user interactions → state transitions (`#purpose-1`), and user interactions → call graphs (`#purpose-2`). 

## Task
Roughly, here are the passes you should perform:
1. Investigate the major features and the interactions the user can have with the project, grouped by feature. 
2. For each feature, succinctly enumerate the various state transitions associated with it, if any.
3. For each feature, List the big ticket code components involved with the feature, by call order, from client to backend. Associate components with major state transitions.
4. For each feature, step by step, like a compiler recording the state machine, specify the call graph exactly. Keep track of the passed values and thereby the state from step to step.

---

## EXAMPLE ARCHITECTURE.md

The following is a high quality ARCHITECTURE.md of a CLI tool called 'onefilellm', which describes itself: ”Specify a github or local repo, github pull request, arXiv or Sci-Hub paper, Youtube transcript or documentation URL on the web and scrape into a text file and clipboard for easier LLM ingestion“.
The project is utterly different from the current project but I find its ARCHITECTURE.md well-written. Therefore, ignore onefilellm's domain entirely and focus on the generalizable reasons the file is good, to ultimately apply it on the ARCHITECTURE.md file you will build:

<Example ARCHITECTURE.md>

## Architecture Diagram (Space)

> Focus: The "City Map". Structural boundaries, where things "live", high-level grouping, and external relationships.
> Answers: What are the major building blocks of the system? (e.g., "There is a User, a CLI Tool, and a Processing Engine.")


```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXTERNAL WORLD                                                         │
│                                                                         │
│  ┌────────┐       ┌───────────────────────────────┐      ┌───────────┐  │
│  │  USER  │──────►│  CLI INPUT (Url/Path/Repo)    │◄─────│ FILE SYS  │  │
│  └────────┘       └──────────────┬────────────────┘      └───────────┘  │
│                                  │                                      │
╞══════════════════════════════════│══════════════════════════════════════╡
│  ONEFILELLM (System Boundary)    │                                      │
│                                  ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                        CONTROLLER (Main)                          │  │
│  │  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐  │  │
│  │  │ Source Detector │──►│ Dispatcher      │──►│ Output Handler  │  │  │
│  │  └─────────────────┘   └────────┬────────┘   └────────┬────────┘  │  │
│  └─────────────────────────────────│─────────────────────│───────────┘  │
│                                    │                     │              │
│          ┌─────────────────────────▼─────────────────────▼──────────┐   │
│          │                 PROCESSING MODULES                       │   │
│          │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │   │
│          │ │ GitHub   │ │ ArXiv    │ │ YouTube  │ │ Local FS │ ...  │   │
│          │ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘      │   │
│          └──────│────────────│────────────│────────────│────────────┘   │
╞═════════════════│════════════│════════════│════════════│════════════════╡
│  EXTERNAL SVCS  ▼            ▼            ▼            ▼                │
│            ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐            │
│            │ GITHUB │   │ ARXIV  │   │ YOUTUBE│   │ OS API │            │
│            └────────┘   └────────┘   └────────┘   └────────┘            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagram  (Time)

> Focus: The "Movie Script". Chronology, Interactions, Control Flow.
> Answers: Who talks to whom, and in what order?

```
TIME   ACTOR              ACTION                                TARGET
│
├───►  User               Runs script `onefilellm.py`       ──► System
│
├───►  System             Detects input type (GitHub URL)   ──► Self
│
├───►  System             Requests Repo Content             ──► GitHub API
│      GitHub API         Returns File List                 ──► System
│
├───►  System             Iterates over files               ──► Self
│      │                  ├── Downloads File 1
│      │                  ├── Downloads File 2
│      │                  └── Downloads File 3
│
├───►  System             Extracts Text from files          ──► Processing
│
├───►  Processing         Cleans & Compresses Text          ──► Filesystem
│      Processing         Copies to Clipboard               ──► Clipboard
│
└───►  System             Prints Token Count                ──► User
```

---

## Data Flow Diagram (Matter)

> Focus: The dynamic transformation. Inputs, Outputs, Storage, State. The mutation of state/data as it moves through the pipes.
> Answers: Where does the data come from, how does it change, and where does it end up?

```
[ RAW INPUT ]        [ INGESTION ]        [ TRANSFORMATION ]       [ OUTPUT ]
(URL / Path)         (Fetching)           (Cleaning/Formatting)    (Files/Clip)

                     ┌──────────────┐     ┌──────────────────┐
GitHub URL ───────►  │ GitHub API   │──►  │ 1. Stopwords     │
                     └──────────────┘     │ 2. Lowercase     │     ┌────────────┐
                     ┌──────────────┐     │ 3. Regex Clean   │──┬─►│ uncomp.txt │
Youtube URL ──────►  │ Transcript   │──►  │                  │  │  └────────────┘
                     └──────────────┘     └──────────────────┘  │
                     ┌──────────────┐                           │  ┌────────────┐
Local Path ───────►  │ File Read    │───────────────────────────┼─►│ compr.txt  │
                     └──────────────┘                           │  └────────────┘
                                                                │
                                                                │  ┌────────────┐
                                                                └─►│ Clipboard  │
                                                                   └────────────┘
```

---

## Call Graph (Logic)
The static wiring. The rigid hierarchy of "what controls what" inside the code.
> Focus: Execution depth and runtime symbol dependencies.
> Answers: When A runs, exactly which other symbols does it trigger?

```
main()
├── I/O Operations
│   ├── safe_file_read()
│   └── pyperclip.copy()
│
├── Routing Logic
│   ├── process_github_repo()
│   │   ├── requests.get()
│   │   └── download_file()
│   │
│   ├── process_arxiv_pdf()
│   │   ├── requests.get()
│   │   └── PdfReader().pages
│   │
│   ├── fetch_youtube_transcript()
│   │   └── YouTubeTranscriptApi.get_transcript()
│   │
│   └── crawl_and_extract_text()
│       ├── requests.get()
│       └── BeautifulSoup()
│
├── Text Processing
│   └── preprocess_text()
│       ├── re.sub()
│       └── nltk.stop_words
│
└── Analytics
    └── get_token_count()
        └── tiktoken.encode()
```
</Example ARCHITECTURE.md>

---

Keep in mind the instructions of 'Purpose', 'Strategy' and 'Task' sections.