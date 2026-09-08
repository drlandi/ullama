#ifndef ULLAMA_H
#define ULLAMA_H

#include <stdbool.h>
#include <stddef.h>
#include "llama.h"

// Configuration structure for our lightweight 8GB-optimized runtime
typedef struct {
    const char *model_path;
    int n_ctx;
    int n_threads;
    bool use_mmap;
} ullama_config_t;

// Function prototypes for system tracking and RAM safety guards
void ullama_print_system_memory(void);
bool ullama_check_ram_headroom(size_t required_mb);

#endif // ULLAMA_H