# uLLAMA

A small C program that runs a local language model through [llama.cpp](https://github.com/ggml-org/llama.cpp), plus a Python **eval harness** that measures what a small local model can and cannot build when every answer is checked by a test, and a benchmark of one thing the harness built: a binary search over a 100-million-record file.

Everything was written as a learning project (42 São Paulo, Pop!_OS, 8 GB RAM, CPU only). This README says what was measured and what was not.

- **`src/`** is the engine: load a GGUF model, keep a multi-turn chat, stream tokens.
- **`factory/`** is the harness: give a small model a task, run a human-written judge on its code, retry, and count how often it passes. It also holds the benchmark script.
- **`search/`** holds the function the harness produced and a human reviewed (see "Searching a record file"), and `search/c/`, a human-written C version that uses `mmap` (see "C version with mmap").

## Engine

```
src/
  main.c     argument handling, REPL, pipe mode
  engine.c   model and context setup, sampler chain, cleanup
  chat.c     chat history and chat-template rendering
  gen.c      tokenizing, decoding, the sampling loop, timing
  ullama.h   shared types and prototypes
  Makefile
```

What it does:

- Applies the model's own chat template (`llama_chat_apply_template`) and keeps the conversation history, so multi-turn chat works. When the context (4096 tokens) or the message history fills up, the chat resets instead of failing.
- Samples with top-k 40, top-p 0.9, temperature 0.7 and a random seed. Generation stops at the model's end-of-generation token or after 1024 tokens.
- Three ways to run it:
  - `./ullama model.gguf` starts an interactive chat when stdin is a terminal.
  - `./ullama model.gguf "prompt"` answers one prompt.
  - `echo "prompt" | ./ullama model.gguf` reads all of stdin as one prompt.
- Only the completion goes to stdout. Statistics (`[N tok, X tok/s]`) and real errors go to stderr, so other programs can consume the output directly.
- Written to the 42 Norm (5 functions per file, 25 lines per function). `norminette` passed on all files when they were written; run it yourself after any change.

### Build

Needs a built llama.cpp (shared libraries in `build/bin`) and a GGUF model.

```bash
cd src
make                                  # expects llama.cpp in ~/tools/llama.cpp
make LLAMA_DIR=/path/to/llama.cpp     # or point it somewhere else
./ullama ../models/Qwen2.5-1.5B-Instruct-Q4_K_M.gguf "Explain recursion in 3 sentences."
```

The Makefile links the ggml libraries directly and sets an `rpath`, so `LD_LIBRARY_PATH` is not needed. That matters if your llama.cpp tree was moved after it was built, because the libraries then carry a stale runpath and the loader cannot find `libggml`. `ldd ./ullama` should show every library resolved.

Models and data files are not in the repo (`models/`, `data/` and `*.bin` are ignored).

## Factory

The rule: **a task passes only when its judge says so.** "The script ran without crashing" is not a test. An early version of this project counted exit code 0 as a pass and reported "10/10 tasks passed", and roughly half of those answers were wrong.

```
factory/
  factory.py        the loop, the retry strategies, the benchmark of the model
  issues.json       tasks: prompt, judge file, output name, status
  tests/            judges and helpers, written by a human and never by the model
  bench_search.py   timing benchmark for a search function on a real data file
  results.jsonl     raw log of every run and benchmark
```

For each task:

1. Send the prompt to `ullama` on stdin and extract the code block.
2. Copy it to `solution.py` in a fresh temporary folder next to the task's judge (and any helper files the judge needs), and run the judge.
3. If it fails, try again (up to 3 attempts), using one of two strategies:
   - **repair**: show the model its previous code and the judge's failure message.
   - **fresh**: ask the original question again; the sampler is random, so each try is a new draw.

Design rules learned along the way:

- **The prompt is a contract.** It names the exact functions and states every rule. The judge cannot check what the prompt did not say.
- **The judge reports what it got and what it expected**, so a failure message is something a model or a person can act on.
- **The judge can check how an answer was found, not only what it is.** The binary-search judges use a list that counts reads and refuses iteration, and the file-search judge counts the bytes read and how often the file is opened and closed.
- **Judges are tested too.** Each one was run against a correct solution and against deliberately broken variants before being trusted.
- **A passing judge is a lower bound.** Reading the passing code found problems the judge missed (see below), and the judge was tightened.

Commands:

```bash
python3 factory/factory.py                                         # run every pending task
python3 factory/factory.py --only 8                                # run one task once and keep its code
python3 factory/factory.py --bench 10 --only 8 --strategy fresh    # measure a task over 10 runs
python3 factory/factory.py --judge FILE --only 8                   # judge a saved file, no model call
```

`--bench` prints how many runs passed and a count of why attempts failed, and saves the failing code to `factory/outputs/bench/` (ignored by git). Set `ULLAMA_MODEL` to use a different model.

## Measured results

Setup: 3 attempts per run, 10 runs per configuration, judge and sampler settings fixed unless stated. Models: Qwen2.5-1.5B-Instruct Q4_K_M (about 1 GB, roughly 18 tok/s here) and Qwen2.5-Coder-3B-Instruct Q4_K_M (1.9 GB, about 9 tok/s). Ten runs is a small sample: the same configuration scored 2/10 once and 0/10 the next time, so only large differences mean anything.

### Word frequency

The rule: an apostrophe inside a word stays in the word (`don't` is one word, `'quoted'` loses its quotes) and accented letters stay whole.

| Configuration | Runs passed | Single attempts passed |
|---|---|---|
| 1.5B, repair retries | 0 / 10 | 0 / 30 |
| 1.5B, fresh retries | 2 / 10 | 2 / 27 |
| 1.5B, fresh retries, repeat of the same run | 0 / 10 | 0 / 30 |
| 3B coder, fresh retries | 3 / 10 | 3 / 26 |
| 1.5B, fresh retries, **prompt adds an approach hint** | **7 / 10** | **7 / 22** |

### 24-byte binary record

`pack_record` / `unpack_record`: an 8-byte big-endian key, a 16-byte NUL-padded ASCII payload, `ValueError` on invalid input.

| Configuration | Runs passed | Single attempts passed |
|---|---|---|
| 1.5B, fresh, prompt only says "use the struct module" | 0 / 10 | 0 / 30 |
| 1.5B, fresh, **prompt gives the format string `>Q16s` and how `s` fields behave** | **5 / 10** | **5 / 26** |

### Searching a record file

`search_file(path, key)`: binary search over a sorted file of 24-byte records, returning the record index or -1, without reading the whole file. The judge compares every answer with an in-memory oracle on files of 0 to 3 records and on a 200,000-record file.

| Configuration | Runs passed | Single attempts passed |
|---|---|---|
| Judge v1 (answers and bytes read). 1.5B, fresh retries | 0 / 10 | 0 / 30 |
| Judge v1. 1.5B, repair retries | 0 / 10 | 0 / 30 |
| Judge v1. 3B coder, fresh retries | 10 / 10 | 10 / 14 |
| Judge v2 (also: open the file at most once, and close it). 3B coder, fresh | 1 / 10 | 1 / 30 |
| Judge v2, **prompt adds a structural hint** (open once in a `with` block, start with `import os`). 3B coder, fresh | **10 / 10** | **10 / 13** |

Reading the code that passed judge v1 showed it opened the file inside the loop on every probe and leaked the handle when the key was found. The judge did not check either, so it was tightened (v2). The same model then passed 1 of 10 runs, until the prompt spelled out the file-handling structure. Almost every failure in these runs was plumbing (a missing `import os`, a file handle used outside its `with` block, opening or closing the file wrongly), not the search algorithm.

### Search benchmark

The function from the last row of the previous table (`search/search_file.py`) was timed on generated files of sorted records, with sorted keys separated by random gaps. `factory/bench_search.py` first checks all 2,000 answers (half present keys, half absent) against an independent oracle, then times each lookup. The first pass starts after asking the kernel to drop the file from the page cache (`posix_fadvise`), the second pass repeats the same queries. Each timing is one call of `search_file(path, key)`, so it includes a file size check, an `open` and a close.

| Records | File | Cold first pass, median (p95 / p99) | Warm, median (p99) | Linear scan, per query |
|---|---|---|---|---|
| 1 million | 24 MB | 42.8 µs (1,002 / 1,531 µs) | 40.4 µs (61.5 µs) | 73.9 ms |
| 100 million | 2.4 GB | 1,624 µs (2,323 / 2,714 µs) | 59.9 µs (87.4 µs) | 5,467 ms (2 queries) |

- The 100-million run was done twice; the medians were 1,747 and 1,624 µs cold and 59.5 and 59.9 µs warm.
- Warm latency grew about 1.5 times for a 100 times larger file, which is what a binary search should do. Cold, the 100-million file was about 27 times slower than warm, so a lookup is limited by disk reads.
- At 1 million records the "cold" pass is only cold at the start: the tail (p95 about 1 ms) shows the disk reads, and the median shows the file becoming cached during the pass. A median alone would hide that.
- The linear scan is a rough baseline (2 queries at 100 million: one absent key that must read the whole file, and one present key that stops earlier). Treat it as an order of magnitude.
- The measuring tool itself can disturb the measurement: the first version of the benchmark read the answer pages while building its oracle, which warmed exactly the pages the "cold" pass needed. Dropping the cache after building the queries fixed that.

## C version with mmap

`search/c/` is a human-written C version (not produced by the factory), written to the 42 Norm and checked with `norminette` and `-Wall -Wextra -Werror`. It exists to answer one question: how much of the roughly 60 µs Python lookup is Python?

It does not use its own oracle. `factory/bench_search.py --export-queries` writes the same 2,000 queries and their correct answers that the Python benchmark uses, and the C program verifies every answer before reporting a time (a deliberately wrong search aborts with the same mismatch the Python benchmark reports). There are two modes: `percall` opens, maps, searches, unmaps and closes the file on every lookup, like the Python function; `mapped` maps the file once and times only the search. It also reports minor and major page faults per query. Setting `MSEARCH_RANDOM=1` applies `madvise(MADV_RANDOM)` to the mapping, which turns kernel readahead off.

```bash
cd search/c && make re && cd ../..        # use make re; touching files can leave stale objects
python3 factory/bench_search.py search/search_file.py data/records_100M.bin --export-queries data/q_100M.bin
search/c/msearch_bench data/records_100M.bin data/q_100M.bin percall     # or: mapped
MSEARCH_RANDOM=1 search/c/msearch_bench data/records_100M.bin data/q_100M.bin mapped
```

Results on the 100-million-record file (2.4 GB), 2,000 queries, same machine. The Python row is the benchmark from above; the C rows are from later runs, and warm figures are the range over repeated runs.

| Variant | Cold median | Cold p99 | Cold major faults per query | Warm median | Warm p99 | Warm minor faults per query |
|---|---|---|---|---|---|---|
| Python, per call | 1,697 µs | 3,153 µs | not counted | 58.5 µs | 88.1 µs | not counted |
| C `mmap`, per call | 688 µs | 11,214 µs | 1.61 | 59.8 to 63.3 µs | 92 to 150 µs | 15.1 |
| C `mmap`, per call, `MADV_RANDOM` | 1,611 µs | 2,757 µs | 8.30 | 37.1 to 40.2 µs | 62 to 85 µs | 15.1 |
| C `mmap`, mapped once | 808 µs | 11,348 µs | 1.61 | 1.4 to 1.8 µs | 7 to 8 µs | 0 |
| C `mmap`, mapped once, `MADV_RANDOM` | 1,654 µs | 2,851 µs | 8.30 | 1.2 µs | 7.0 µs | 0 |

What the measurements show:

- **The language is not where the time goes.** A C lookup that opens and maps the file every time costs about the same as the Python one (about 60 µs against about 59 µs). The same C search on a file that is already mapped takes 1.2 to 1.8 µs, which is about 30 to 45 times less. Keeping the file open or mapped matters far more than the choice of language.
- **Per-call mapping costs about 15 minor page faults per lookup;** a file mapped once costs none.
- **Kernel readahead causes the cold tail in the `mmap` version.** With the default setting the C cold p99 is about 11 ms (11.2 to 11.6 ms over four runs for per-call, 10.5 to 11.9 ms for mapped). With `MADV_RANDOM` it drops to about 2.8 ms and the maximum from 18 to 25 ms to about 4 ms, at the price of a doubled median (about 0.8 ms to 1.65 ms) because each probe becomes its own small random read (8.3 major faults per query instead of 1.6). With readahead off the C cold profile is close to the Python one.
- **Cold latency is roughly eight disk reads.** 8.3 major faults per query at about 0.2 ms each is about 1.65 ms.
- **`MADV_RANDOM` also lowered the warm per-call latency** from about 60 µs to about 38 µs (four runs, three of them interleaved with default-setting runs), with the same number of faults per lookup. The reason was not established.

What was not established: how the roughly 60 µs of the per-call version splits between page faults and the `open`, `mmap`, `munmap` and `close` calls; why `MADV_RANDOM` lowers the warm per-call time; and whether these effects are specific to this machine and disk (the disk type was not checked). One early C per-call run measured 82 µs warm and did not repeat in six later runs, so it is not used. The timer (`clock_gettime`) costs roughly 20 to 30 ns per lookup, which is small against microseconds but visible against the 1.2 to 1.8 µs mapped search.

## What the numbers support

- **How the task is specified mattered most.** Pooling the two no-hint word-frequency benchmarks, a single attempt passed about 3.5% of the time (2/57); with an approach hint it passed about 32% (7/22), which is very unlikely to be chance (Fisher's exact test, p about 0.002). The format-string hint on the record task moved runs from 0/10 to 5/10 (p about 0.03), and the structural hint on the search task moved them from 1/10 to 10/10 (p about 0.0001).
- **Model size and specialisation mattered on some tasks and not others.** The 3B coder model gave no clear gain on word frequency, where the difficulty was a fiddly rule, but passed the file-search task 10/10 where the 1.5B model passed 0/10 (p about 0.00001). The two models differ in both size and code training, so this does not say which one matters.
- **Retries multiply a low success rate.** A 32% per-attempt rate predicts about 68% of 3-attempt runs passing; 70% was observed. In the repair benchmark on the search task, errors that named their own fix fell (a missing `import os` went from 13 to 6 of 30 attempts), but no failing run became a passing one; with vaguer feedback on the other tasks, repair showed no benefit.
- **Failure histograms guided each fix** and showed when the failures were plumbing and not reasoning.

## Limits, stated plainly

- **The hints are close to the solution.** A human describing the approach in that much detail is doing much of the work. These results say a small model can type a well-described function; they do not say it can design one.
- **Few tasks, two models, one machine.** Nothing here should be generalised beyond that.
- **The 100-million-record file is the largest tested.** A billion records (24 GB) does not fit on the free disk space of the machine used.
- **The factory-built search function is Python.** The C version is human-written, and the factory was not asked to produce it. Python with the file kept open between lookups was not measured, so the Python-versus-C comparison covers only the per-call design.
- **`posix_fadvise` is advisory.** The cold pass is much slower than the warm pass, as expected, but the strongest way to guarantee a cold cache (`echo 3 > /proc/sys/vm/drop_caches`) was not used.
- **The engine was tested on Qwen2.5 models only.** Other chat templates are handled by llama.cpp but were not tried.
- **An early comparison with Ollama** (about 16 to 17 tok/s here against about 11) came from a handful of single runs with different settings (threads, context size, sampler). It is not evidence that this wrapper is faster. A matched comparison with `llama-bench` has not been done.

## Roadmap

1. Split the per-call cost of the C version (page faults against `open`, `mmap`, `munmap`, `close`) and measure Python with the file kept open.
2. A SQLite baseline on the same data.
3. The billion-record run on a drive with enough space.
4. A matched benchmark of the engine against Ollama using `llama-bench`.
