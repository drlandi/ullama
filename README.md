# Project uLLAMA (Micro-Inference & Custom Specialization)

> **Target Hardware (Current)**: ASUS VivoBook / Pop!_OS / 8 GB Soldered RAM / CPU AVX2  
> **Target Hardware (Future)**: AM4 Workstation (Ryzen 5 4600G / 64 GB - 128 GB RAM / Optional RTX GPU)  
> **Core Objective**: Build a lean, high-performance, domain-specific AI development workflow tailored to the complete 42 school curriculum (strict C systems programming, Python, AI modules, Makefiles, and project norms) and AWS Cloud engineering, optimized to run entirely within an 8 GB memory constraint using custom GGUF models and a native C runtime wrapper.

## Directory Structure
- `docs/`: Obsidian vault synced notes, architecture specs, and prompt logs.
- `datasets/`: JSONL training files for 42 C-norms, Python, AI modules, and AWS workflows.
- `colab/`: Unsloth Python training notebooks & export scripts.
- `src/`: Pure C source code for the native uLLAMA runtime wrapper (`ullama.c`, `ullama.h`, `Makefile`).
- `models/`: Local staging ground for compiled .gguf dwarf models.
