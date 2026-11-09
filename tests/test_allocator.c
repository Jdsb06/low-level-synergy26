#include "libmemctl.h"

#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

#define CHECK(expr) do { if (!(expr)) { \
    (void)fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #expr); \
    exit(EXIT_FAILURE); } } while (0)

void *__real_mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
int __real_munmap(void *addr, size_t length);
void *__wrap_mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
int __wrap_munmap(void *addr, size_t length);

static atomic_size_t live_mapping_bytes;
static atomic_int fail_mapping;

void *__wrap_mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset)
{
    void *result;
    if (atomic_load(&fail_mapping)) {
        errno = ENOMEM;
        return MAP_FAILED;
    }
    result = __real_mmap(addr, length, prot, flags, fd, offset);
    if (result != MAP_FAILED) {
        (void)atomic_fetch_add(&live_mapping_bytes, length);
    }
    return result;
}

int __wrap_munmap(void *addr, size_t length)
{
    const int result = __real_munmap(addr, length);
    if (result == 0) {
        (void)atomic_fetch_sub(&live_mapping_bytes, length);
    }
    return result;
}

static uint32_t random_next(uint32_t *state)
{
    *state ^= *state << 13U;
    *state ^= *state >> 17U;
    *state ^= *state << 5U;
    return *state;
}

static void verify(const unsigned char *ptr, size_t length, unsigned char tag)
{
    size_t index;
    CHECK(ptr != NULL);
    CHECK((uintptr_t)ptr % _Alignof(max_align_t) == 0U);
    for (index = 0U; index < length; ++index) {
        CHECK(ptr[index] == tag);
    }
}

static void test_zero_and_boundaries(void)
{
    static const size_t boundaries[] = {
        1U, 16U, 32U, 64U, 128U, 256U, 320U, 1024U, 1280U,
        4096U, 5120U, 16384U, 20480U, 65536U, 65537U, 1048576U
    };
    void *zero[4];
    size_t i;
    size_t j;
    zero[0] = my_malloc(0U);
    zero[1] = my_calloc(0U, SIZE_MAX);
    zero[2] = my_calloc(SIZE_MAX, 0U);
    zero[3] = my_realloc(NULL, 0U);
    for (i = 0U; i < 4U; ++i) {
        CHECK(zero[i] != NULL);
        CHECK((uintptr_t)zero[i] % _Alignof(max_align_t) == 0U);
        for (j = 0U; j < i; ++j) {
            CHECK(zero[i] != zero[j]);
        }
    }
    for (i = 0U; i < 4U; ++i) {
        my_free(zero[i]);
    }
    for (i = 0U; i < sizeof(boundaries) / sizeof(boundaries[0]); ++i) {
        for (j = 0U; j < 3U; ++j) {
            const size_t size = boundaries[i] + j - 1U;
            unsigned char *ptr = my_malloc(size);
            unsigned char *other = my_malloc(size);
            CHECK(ptr != NULL && other != NULL && ptr != other);
            (void)memset(ptr, 0xA6, size);
            (void)memset(other, 0x5B, size);
            verify(ptr, size, 0xA6U);
            verify(other, size, 0x5BU);
            my_free(other);
            my_free(ptr);
        }
    }
    errno = EDOM;
    my_free(NULL);
    CHECK(errno == EDOM);
    (void)puts("PASS zero semantics, alignment and size-class/large boundaries");
}

static void test_failure_atomicity(void)
{
    unsigned char *ptr = my_malloc(113U);
    unsigned char *replacement;
    CHECK(ptr != NULL);
    (void)memset(ptr, 0xCD, 113U);
    memctl_trim(); /* Require a real cache miss before injecting mapping failure. */
    atomic_store(&fail_mapping, 1);
    errno = 0;
    replacement = my_realloc(ptr, 8U * 1024U * 1024U);
    CHECK(replacement == NULL && errno == ENOMEM);
    verify(ptr, 113U, 0xCDU);
    CHECK(my_malloc(128U * 1024U) == NULL);
    atomic_store(&fail_mapping, 0);
    replacement = my_realloc(ptr, 200U);
    CHECK(replacement != NULL);
    verify(replacement, 113U, 0xCDU);
    CHECK(my_realloc(replacement, 0U) == NULL);
    errno = 0;
    CHECK(my_malloc(SIZE_MAX) == NULL && errno == ENOMEM);
    errno = 0;
    CHECK(my_calloc(SIZE_MAX / 3U + 1U, 3U) == NULL && errno == ENOMEM);
    /* A failed new slab must not leave its mutex held. */
    memctl_trim();
    atomic_store(&fail_mapping, 1);
    CHECK(my_malloc(7U) == NULL);
    atomic_store(&fail_mapping, 0);
    ptr = my_malloc(7U);
    CHECK(ptr != NULL);
    my_free(ptr);
    (void)puts("PASS injected mapping failures, realloc preservation and overflow");
}

typedef struct slot {
    unsigned char *ptr;
    size_t size;
    unsigned char tag;
} slot;

typedef struct worker_context {
    uint32_t seed;
    size_t iterations;
} worker_context;

static void *mixed_worker(void *argument)
{
    worker_context *context = argument;
    slot slots[64] = {{0}};
    size_t operation;
    for (operation = 0U; operation < context->iterations; ++operation) {
        const uint32_t value = random_next(&context->seed);
        slot *item = &slots[value % 64U];
        const size_t size = (value >> 8U) % 8193U;
        if (item->ptr != NULL) {
            verify(item->ptr, item->size, item->tag);
            if (value % 3U == 0U) {
                my_free(item->ptr);
                item->ptr = NULL;
            } else {
                unsigned char *next = my_realloc(item->ptr, size);
                if (size == 0U) {
                    CHECK(next == NULL);
                } else {
                    CHECK(next != NULL);
                    verify(next, item->size < size ? item->size : size, item->tag);
                }
                item->ptr = next;
                item->size = size;
                if (next != NULL) {
                    (void)memset(next, item->tag, size);
                }
            }
        } else {
            item->ptr = value % 5U == 0U ? my_calloc(size, 1U) : my_malloc(size);
            CHECK(item->ptr != NULL);
            if (value % 5U == 0U) {
                verify(item->ptr, size, 0U);
            }
            item->size = size;
            item->tag = (unsigned char)(value >> 24U);
            (void)memset(item->ptr, item->tag, size);
        }
    }
    for (operation = 0U; operation < 64U; ++operation) {
        if (slots[operation].ptr != NULL) {
            verify(slots[operation].ptr, slots[operation].size, slots[operation].tag);
            my_free(slots[operation].ptr);
        }
    }
    return NULL;
}

static slot transferred[2048];

#ifndef MEMCTL_LARGE_CACHE
#define MEMCTL_LARGE_CACHE 1
#endif
#if MEMCTL_LARGE_CACHE
static void test_large_reuse(void)
{
    unsigned char *ptr;
    unsigned char *next;
    void *objects[48];
    size_t index;
    size_t live_bytes;
    memctl_trim();
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    ptr = my_malloc(65537U);
    CHECK(ptr != NULL);
    memset(ptr, 0xa7, 65537U);
    live_bytes = atomic_load(&live_mapping_bytes);
    errno = EDOM;
    my_free(ptr);
    CHECK(errno == EDOM && atomic_load(&live_mapping_bytes) == live_bytes);
    atomic_store(&fail_mapping, 1);
    next = my_calloc(1, 65537U);
    CHECK(next == ptr); /* Reuse must work even when every new mapping fails. */
    verify(next, 65537U, 0);
    memset(next, 0xb3, 65537U);
    errno = 0;
    CHECK(my_realloc(next, 200000U) == NULL && errno == ENOMEM);
    verify(next, 65537U, 0xb3);
    atomic_store(&fail_mapping, 0);
    ptr = my_realloc(next, 200000U);
    CHECK(ptr != NULL);
    verify(ptr, 65537U, 0xb3);
    memctl_trim(); /* Must retain the live mapping and reclaim only cached ones. */
    CHECK(atomic_load(&live_mapping_bytes) > 0U);
    ptr[199999] = 0x77;
    my_free(ptr);
    memctl_trim();
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    for (index = 0; index < 48U; ++index) {
        objects[index] = my_malloc(65537U + index * 32768U);
        CHECK(objects[index] != NULL);
        memset(objects[index], (int)index, 65537U + index * 32768U);
    }
    for (index = 0; index < 48U; ++index) {
        verify(objects[index], 65537U + index * 32768U, (unsigned char)index);
        my_free(objects[index]);
    }
    CHECK(atomic_load(&live_mapping_bytes) <= 2U * 1024U * 1024U);
    memctl_trim();
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    ptr = my_malloc(4U * 1024U * 1024U);
    CHECK(ptr != NULL);
    my_free(ptr);
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    ptr = my_malloc(1024U * 1024U);
    CHECK(ptr != NULL);
    my_free(ptr);
    CHECK(atomic_load(&live_mapping_bytes) > 0U);
    memctl_trim();
    ptr = my_malloc(1024U * 1024U + 1U);
    CHECK(ptr != NULL);
    my_free(ptr);
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    puts("PASS large cache reuse/zeroing, miss failure atomicity, shared cap and live-safe trim");
}
#endif

static void test_region_exhaustion(void)
{
    static const size_t sizes[] = {24U, 8193U, 65536U};
    slot items[5000];
    size_t group;
    size_t index;
    for (group = 0U; group < 3U; ++group) {
        const size_t count = group == 0U ? 5000U : 100U;
        for (index = 0U; index < count; ++index) {
            items[index].size = sizes[group];
            items[index].tag = (unsigned char)(index % 251U + 1U);
            items[index].ptr = my_malloc(items[index].size);
            CHECK(items[index].ptr != NULL);
            (void)memset(items[index].ptr, items[index].tag, items[index].size);
        }
        for (index = 0U; index < count; index += 2U) {
            my_free(items[index].ptr);
        }
        memctl_trim();
        for (index = 0U; index < count; index += 2U) {
            items[index].ptr = my_malloc(items[index].size);
            CHECK(items[index].ptr != NULL);
            items[index].tag ^= 0x55U;
            (void)memset(items[index].ptr, items[index].tag, items[index].size);
        }
        for (index = count; index > 0U; --index) {
            slot *item = &items[index - 1U];
            verify(item->ptr, item->size, item->tag);
            my_free(item->ptr);
        }
    }
    (void)puts("PASS full-region exhaustion, holes, reuse and trim with live objects");
}

static void *concurrent_trimmer(void *unused)
{
    size_t index;
    (void)unused;
    for (index = 0U; index < 500U; ++index) {
        memctl_trim();
    }
    return NULL;
}

static void *producer(void *unused)
{
    size_t index;
    (void)unused;
    for (index = 0U; index < 2048U; ++index) {
        slot *item = &transferred[index];
        item->size = index * 37U % 70001U;
        item->tag = (unsigned char)index;
        item->ptr = my_malloc(item->size);
        CHECK(item->ptr != NULL);
        (void)memset(item->ptr, item->tag, item->size);
    }
    return NULL;
}

static void *consumer(void *argument)
{
    const size_t start = *(const size_t *)argument;
    size_t index;
    for (index = start; index < 2048U; index += 8U) {
        slot *item = &transferred[index];
        unsigned char *resized;
        verify(item->ptr, item->size, item->tag);
        resized = my_realloc(item->ptr, item->size + 197U);
        CHECK(resized != NULL);
        verify(resized, item->size, item->tag);
        my_free(resized);
    }
    return NULL;
}

static void test_threads_and_reclamation(void)
{
    pthread_t threads[8];
    worker_context contexts[8];
    pthread_t trimmer;
    size_t starts[8];
    size_t index;
    CHECK(pthread_create(&threads[0], NULL, producer, NULL) == 0);
    CHECK(pthread_join(threads[0], NULL) == 0);
    /* Producer has exited before consumers use/free its objects. */
    for (index = 0U; index < 8U; ++index) {
        starts[index] = index;
        CHECK(pthread_create(&threads[index], NULL, consumer, &starts[index]) == 0);
    }
    for (index = 0U; index < 8U; ++index) {
        CHECK(pthread_join(threads[index], NULL) == 0);
    }
    (void)puts("PASS cross-thread realloc/free after producer thread exit");
    for (index = 0U; index < 8U; ++index) {
        contexts[index].seed = UINT32_C(0x719AC805) + (uint32_t)index * 53U;
        contexts[index].iterations = 30000U;
        CHECK(pthread_create(&threads[index], NULL, mixed_worker, &contexts[index]) == 0);
    }
    CHECK(pthread_create(&trimmer, NULL, concurrent_trimmer, NULL) == 0);
    for (index = 0U; index < 8U; ++index) {
        CHECK(pthread_join(threads[index], NULL) == 0);
    }
    CHECK(pthread_join(trimmer, NULL) == 0);
    CHECK(atomic_load(&live_mapping_bytes) <= 2U * 1024U * 1024U);
    memctl_trim();
    CHECK(atomic_load(&live_mapping_bytes) == 0U);
    (void)puts("PASS 240000 seeded mixed operations; bounded cache; zero mappings after trim");
}

int main(void)
{
    test_zero_and_boundaries();
    test_failure_atomicity();
#if MEMCTL_LARGE_CACHE
    test_large_reuse();
#endif
    test_region_exhaustion();
    test_threads_and_reclamation();
    (void)puts("All independent allocator tests passed.");
    return 0;
}
