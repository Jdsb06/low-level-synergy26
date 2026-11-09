#ifndef MEMCTL_BENCH_PROFILE_H
#define MEMCTL_BENCH_PROFILE_H

/* Harness utilities only; libc allocation is never linked into allocator.o. */
#include "libmemctl.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef MEMCTL_LIBC
#include <malloc.h>
#define ALLOC malloc
#define RELEASE free
#define RESIZE realloc
#define ZERO_ALLOC calloc
static inline void profile_trim(void) { (void)malloc_trim(0); }
#else
#define ALLOC my_malloc
#define RELEASE my_free
#define RESIZE my_realloc
#define ZERO_ALLOC my_calloc
static inline void profile_trim(void) { memctl_trim(); }
#endif

static inline void require(int success)
{
    if (!success) {
        fputs("profile setup, allocation or payload validation failed\n", stderr);
        exit(2);
    }
}

static inline unsigned long number(const char *text, unsigned long limit)
{
    char *end;
    unsigned long value;
    errno = 0;
    value = strtoul(text, &end, 10);
    require(errno == 0 && end != text && *end == '\0' && value > 0 && value <= limit);
    return value;
}

static inline uint32_t random_next(uint32_t *seed)
{
    *seed ^= *seed << 13U;
    *seed ^= *seed >> 17U;
    *seed ^= *seed << 5U;
    return *seed;
}

#endif
