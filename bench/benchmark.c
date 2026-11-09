#include "libmemctl.h"

#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>

#define SLOTS 128U
#define MAX_THREADS 64U

typedef struct context {
    uint32_t seed;
    size_t operations;
    int kind;
    int bad;
} context;

typedef struct allocation {
    unsigned char *ptr;
    size_t size;
    unsigned char tag;
} allocation;

static pthread_barrier_t ready;
static pthread_barrier_t start;
static pthread_barrier_t finish;

static void require(int success)
{
    if (!success) {
        (void)fprintf(stderr, "benchmark setup or allocation failure\n");
        exit(EXIT_FAILURE);
    }
}

static uint32_t next_random(uint32_t *seed)
{
    *seed ^= *seed << 13U;
    *seed ^= *seed >> 17U;
    *seed ^= *seed << 5U;
    return *seed;
}

static size_t choose_size(uint32_t value, int kind)
{
    static const size_t small[] = {16U, 24U, 48U, 96U, 192U, 384U, 768U, 1024U};
    static const size_t mixed[] = {1U, 31U, 97U, 257U, 769U, 2049U, 4097U, 8193U, 16385U};
    if (kind == 0) {
        return small[value % (sizeof(small) / sizeof(small[0]))];
    }
    if (kind == 1) {
        return mixed[value % (sizeof(mixed) / sizeof(mixed[0]))];
    }
    return 65537U + value % 131072U;
}

static void workload(context *item, allocation *slots, size_t operations)
{
    size_t operation;
    for (operation = 0U; operation < operations; ++operation) {
        const uint32_t value = next_random(&item->seed);
        allocation *slot = &slots[value % SLOTS];
        const size_t size = choose_size(value >> 8U, item->kind);
        if (slot->ptr == NULL) {
            slot->ptr = my_malloc(size);
            require(slot->ptr != NULL);
            slot->size = size;
            slot->tag = (unsigned char)(value >> 24U);
        } else {
            if (slot->ptr[0] != slot->tag || slot->ptr[slot->size - 1U] != slot->tag) {
                item->bad = 1;
            }
            if (value % 4U == 0U) {
                unsigned char *next = my_realloc(slot->ptr, size);
                require(next != NULL);
                if (next[0] != slot->tag) {
                    item->bad = 1;
                }
                slot->ptr = next;
                slot->size = size;
            } else {
                my_free(slot->ptr);
                slot->ptr = NULL;
            }
        }
        if (slot->ptr != NULL) {
            slot->ptr[0] = slot->tag;
            slot->ptr[slot->size - 1U] = slot->tag;
        }
    }
}

static void release_slots(allocation *slots)
{
    size_t index;
    for (index = 0U; index < SLOTS; ++index) {
        my_free(slots[index].ptr);
        slots[index].ptr = NULL;
    }
}

static void *worker(void *argument)
{
    context *item = argument;
    allocation slots[SLOTS] = {{0}};
    /* Warm initialization/caches, then begin the declared measured trace. */
    workload(item, slots, 2000U);
    release_slots(slots);
    (void)pthread_barrier_wait(&ready);
    (void)pthread_barrier_wait(&start);
    workload(item, slots, item->operations);
    (void)pthread_barrier_wait(&finish);
    release_slots(slots);
    return NULL;
}

static unsigned long status_kib(const char *key)
{
    char line[256];
    unsigned long value = 0UL;
    FILE *file = fopen("/proc/self/status", "r");
    require(file != NULL);
    while (fgets(line, sizeof(line), file) != NULL) {
        if (strncmp(line, key, strlen(key)) == 0) {
            require(sscanf(line + strlen(key), "%lu", &value) == 1);
            break;
        }
    }
    require(fclose(file) == 0);
    return value;
}

static void trim_if_available(void)
{
#ifndef MEMCTL_REFERENCE
    memctl_trim();
#endif
}

static void measure_space(void)
{
    void *pointers[4096];
    unsigned long before_vm;
    unsigned long before_rss;
    unsigned long peak_vm;
    unsigned long peak_rss;
    unsigned long freed_vm;
    unsigned long freed_rss;
    unsigned long trimmed_vm;
    unsigned long trimmed_rss;
    size_t payload = 0U;
    size_t index;
    void *initial = my_malloc(1U);
    require(initial != NULL);
    my_free(initial);
    trim_if_available();
    before_vm = status_kib("VmSize:");
    before_rss = status_kib("VmRSS:");
    for (index = 0U; index < 4096U; ++index) {
        const size_t size = choose_size((uint32_t)index, 1);
        pointers[index] = my_malloc(size);
        require(pointers[index] != NULL);
        (void)memset(pointers[index], 0x5C, size);
        payload += size;
    }
    peak_vm = status_kib("VmSize:");
    peak_rss = status_kib("VmRSS:");
    for (index = 0U; index < 4096U; ++index) {
        my_free(pointers[index]);
    }
    freed_vm = status_kib("VmSize:");
    freed_rss = status_kib("VmRSS:");
    trim_if_available();
    trimmed_vm = status_kib("VmSize:");
    trimmed_rss = status_kib("VmRSS:");
    (void)printf("{\"payload_bytes\":%zu,\"before_vm_kib\":%lu,\"before_rss_kib\":%lu,"
                 "\"held_vm_kib\":%lu,\"held_rss_kib\":%lu,\"freed_vm_kib\":%lu,"
                 "\"freed_rss_kib\":%lu,\"trimmed_vm_kib\":%lu,\"trimmed_rss_kib\":%lu}\n",
                 payload, before_vm, before_rss, peak_vm, peak_rss, freed_vm,
                 freed_rss, trimmed_vm, trimmed_rss);
}

static unsigned long parse_number(const char *text, unsigned long limit)
{
    char *end;
    unsigned long value;
    errno = 0;
    value = strtoul(text, &end, 10);
    require(errno == 0 && end != text && *end == '\0' && value > 0UL && value <= limit);
    return value;
}

int main(int argc, char **argv)
{
    pthread_t threads[MAX_THREADS];
    context contexts[MAX_THREADS];
    struct timespec begin;
    struct timespec end;
    struct rusage usage;
    unsigned int count;
    unsigned int index;
    size_t operations;
    uint32_t seed;
    int kind;
    int bad = 0;
    double seconds;
    if (argc == 2 && strcmp(argv[1], "space") == 0) {
        measure_space();
        return 0;
    }
    if (argc != 5) {
        (void)fprintf(stderr, "usage: %s THREADS OPS_PER_THREAD SEED small|mixed|large\n", argv[0]);
        return 2;
    }
    count = (unsigned int)parse_number(argv[1], MAX_THREADS);
    operations = (size_t)parse_number(argv[2], 10000000UL);
    seed = (uint32_t)parse_number(argv[3], UINT32_MAX);
    kind = strcmp(argv[4], "small") == 0 ? 0 : strcmp(argv[4], "mixed") == 0 ? 1 : 2;
    require(kind != 2 || strcmp(argv[4], "large") == 0);
    require(pthread_barrier_init(&ready, NULL, count + 1U) == 0);
    require(pthread_barrier_init(&start, NULL, count + 1U) == 0);
    require(pthread_barrier_init(&finish, NULL, count + 1U) == 0);
    for (index = 0U; index < count; ++index) {
        contexts[index].seed = seed + index * UINT32_C(0x9E3779B9);
        if (contexts[index].seed == 0U) {
            contexts[index].seed = 1U;
        }
        contexts[index].operations = operations;
        contexts[index].kind = kind;
        contexts[index].bad = 0;
        require(pthread_create(&threads[index], NULL, worker, &contexts[index]) == 0);
    }
    (void)pthread_barrier_wait(&ready);
    require(clock_gettime(CLOCK_MONOTONIC, &begin) == 0);
    (void)pthread_barrier_wait(&start);
    (void)pthread_barrier_wait(&finish);
    require(clock_gettime(CLOCK_MONOTONIC, &end) == 0);
    seconds = (double)(end.tv_sec - begin.tv_sec) + (double)(end.tv_nsec - begin.tv_nsec) * 1e-9;
    for (index = 0U; index < count; ++index) {
        require(pthread_join(threads[index], NULL) == 0);
        bad |= contexts[index].bad;
    }
    require(getrusage(RUSAGE_SELF, &usage) == 0);
    (void)printf("{\"threads\":%u,\"operations\":%zu,\"seconds\":%.9f,"
                 "\"ops_per_second\":%.3f,\"maxrss_kib\":%ld,\"correct\":%s}\n",
                 count, operations * count, seconds, (double)(operations * count) / seconds,
                 usage.ru_maxrss, bad ? "false" : "true");
    return bad ? 1 : 0;
}
