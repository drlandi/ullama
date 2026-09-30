# uLLAMA

A small C program that runs a local language model through [llama.cpp](https://github.com/ggml-org/llama.cpp), plus a Python **eval harness** that measures what a small local model can and cannot build when every answer is checked by a test.

Both parts were written as a learning project (42 São Paulo, Pop!_OS, 8 GB RAM, CPU only). This README says what was measured and what was not.

- **`src/`** is the engine: load a GGUF model, keep a multi-turn chat, stream tokens.
- **`factory/`** is the harness: give a small model a task, run a human-written judge on its code, retry, and count how often it passes.

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

Models are not in the repo (`models/` is ignored).

## Factory

The rule: **a task passes only when its judge says so.** "The script ran without crashing" is not a test. An early version of this project counted exit code 0 as a pass and reported "10/10 tasks passed", and roughly half of those answers were wrong.

```
factory/
  factory.py    the loop, the retry strategies, the benchmark
  issues.json   tasks: prompt, judge file, output name, status
  tests/        judges, written by a human and never by the model
  results.jsonl raw log of every run and benchmark
```

For each task:

1. Send the prompt to `ullama` on stdin and extract the code block.
2. Copy it to `solution.py` in a fresh temporary folder next to the task's judge, and run the judge.
3. If it fails, try again (up to 3 attempts), using one of two strategies:
   - **repair**: show the model its previous code and the judge's failure message.
   - **fresh**: ask the original question again; the sampler is random, so each try is a new draw.

Design rules learned along the way:

- **The prompt is a contract.** It names the exact functions and states every rule. The judge cannot check what the prompt did not say.
- **The judge reports what it got and what it expected**, so a failure message is something a model or a person can act on.
- **The judge can check how an answer was found, not only what it is.** The binary-search judge uses a list that counts reads and refuses iteration, so a linear scan fails with "needed 1000000 reads; a binary search needs about 21".
- **Judges are tested too.** Each one was run against a correct solution and against deliberately broken variants before being trusted.

Commands:

```bash
python3 factory/factory.py                                   # run every pending task
python3 factory/factory.py --bench 10 --only 1 --strategy fresh   # measure a task over 10 runs
python3 factory/factory.py --judge FILE --only 5             # judge a saved file, no model call
```

`--bench` prints how many runs passed and a count of why attempts failed, and saves the failing code to `factory/outputs/bench/` (ignored by git). Set `ULLAMA_MODEL` to benchmark a different model.

## Measured results

Setup: 3 attempts per run, 10 runs per configuration, judge and sampler settings fixed. Models: Qwen2.5-1.5B-Instruct Q4_K_M (about 1 GB, roughly 18 tok/s here) and Qwen2.5-Coder-3B-Instruct Q4_K_M (1.9 GB, about 9.6 tok/s). Ten runs is a small sample: the same configuration scored 2/10 once and 0/10 the next time, so only large differences mean anything.

**Task: word frequency**, with the rule that an apostrophe inside a word stays in the word (`don't` is one word, `'quoted'` loses its quotes) and accented letters stay whole.

| Configuration | Runs passed | Single attempts passed |
|---|---|---|
| 1.5B, repair retries | 0 / 10 | 0 / 30 |
| 1.5B, fresh retries | 2 / 10 | 2 / 27 |
| 1.5B, fresh retries, repeat of the same run | 0 / 10 | 0 / 30 |
| 3B coder, fresh retries | 3 / 10 | 3 / 26 |
| 1.5B, fresh retries, **prompt adds an approach hint** | **7 / 10** | **7 / 22** |

**Task: 24-byte binary record** (`pack_record` / `unpack_record`: 8-byte big-endian key, 16-byte NUL-padded ASCII payload, `ValueError` on invalid input).

| Configuration | Runs passed | Single attempts passed |
|---|---|---|
| 1.5B, fresh, prompt only says "use the struct module" | 0 / 10 | 0 / 30 |
| 1.5B, fresh, **prompt gives the format string `>Q16s` and how `s` fields behave** | **5 / 10** | **5 / 26** |

What the numbers support:

- **How the task is specified mattered most.** Pooling the two no-hint word-frequency benchmarks, a single attempt passed about 3.5% of the time (2/57); with an approach hint it passed about 32% (7/22). By Fisher's exact test that difference is very unlikely to be chance (p about 0.002). For the record task the format-string hint moved runs from 0/10 to 5/10 (p about 0.03).
- **Doubling the model size helped much less** than the hint (about 12% per attempt against 3.5%, at 2.3 times the time), and that gap is within noise for this sample size.
- **Repair prompts did not help** with the 1.5B model here: none of the 20 repair attempts in the first benchmark passed, while 1 of 17 retry attempts passed with fresh retries. Both counts are too small to say fresh is better, only that repair showed no benefit.
- **Fresh retries multiply a low success rate.** A 32% per-attempt rate predicts about 68% of 3-attempt runs passing; 70% was observed.
- **Failure histograms guided each fix.** Without the format hint, 57% of failed record attempts were `str` versus `bytes` mistakes and misuse of `struct`. With it, layout errors disappeared and the remaining failures moved to hand-written input validation.

## Limits, stated plainly

- **The hints are close to the solution.** A human describing the approach in that much detail is doing much of the work. These results say a 1.5B model can type a well-described function; they do not say it can design one.
- **Two tasks, two models, one machine.** Nothing here should be generalised beyond that.
- **Earlier tasks passed on a single run** (password strength, in-memory binary search) and are not benchmarked.
- **The engine was tested on Qwen2.5 models only.** Other chat templates are handled by llama.cpp but were not tried.
- **An early comparison with Ollama** (about 16 to 17 tok/s here against about 11) came from a handful of single runs with different settings (threads, context size, sampler). It is not evidence that this wrapper is faster. A matched comparison with `llama-bench` has not been done.
- **The search tool this was meant to build does not exist yet.** The record format is done and specified; the sorted-file generator and the `mmap` binary search are next.

## Roadmap

1. Build the record file generator and the binary search over it, with a brute-force scan as the oracle on a 1-million-record sample.
2. Benchmark cold and warm queries at 1 million, 100 million and, disk permitting, 1 billion records (24 bytes each, about 24 GB), against `grep` and SQLite as baselines.
3. Matched benchmark of the engine against Ollama using `llama-bench`.
