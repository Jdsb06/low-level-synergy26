#ifndef LIBMEMCTL_H
#define LIBMEMCTL_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* SYSPROG10 interface; zero-sized allocations are distinct and freeable. */
void *my_malloc(size_t size);
void my_free(void *ptr);
void *my_realloc(void *ptr, size_t size);
void *my_calloc(size_t nmemb, size_t size);

/* Optional: release cached, completely empty regions. Safe with concurrent users. */
void memctl_trim(void);

#ifdef __cplusplus
}
#endif
#endif
