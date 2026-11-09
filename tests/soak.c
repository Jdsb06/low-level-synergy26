#include "libmemctl.h"

#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define WORKERS 8U
#define SLOTS 64U
#define REQUIRE(expr) do { if (!(expr)) { \
    (void)fprintf(stderr, "soak failure line %d: %s\n", __LINE__, #expr); \
    exit(1); } } while (0)

typedef struct object {
    unsigned char *ptr;
    size_t size;
    unsigned char tag;
} object;

typedef struct context {
    size_t id;
    size_t operations;
    uint32_t seed;
} context;

static object handoff[WORKERS][SLOTS];
static pthread_barrier_t barrier;
static size_t transfer_rounds = 512U;

static uint32_t next_random(uint32_t *seed)
{
    *seed ^= *seed << 13U;
    *seed ^= *seed >> 17U;
    *seed ^= *seed << 5U;
    return *seed;
}

static unsigned char byte_at(size_t offset, unsigned char tag)
{
    return (unsigned char)((offset * 131U + (offset >> 8U)) ^ tag);
}

static void fill(object *item)
{
    size_t index;
    for (index = 0U; index < item->size; ++index) item->ptr[index] = byte_at(index, item->tag);
}

static void verify(const object *item, size_t length)
{
    size_t index;
    REQUIRE(item->ptr != NULL);
    REQUIRE((uintptr_t)item->ptr % _Alignof(max_align_t) == 0U);
    for (index = 0U; index < length; ++index) REQUIRE(item->ptr[index] == byte_at(index, item->tag));
}

static size_t varied_size(uint32_t value)
{
    static const size_t edges[] = {
        0U, 1U, 15U, 16U, 17U, 255U, 256U, 257U, 319U, 320U, 321U,
        1023U, 1024U, 1025U, 4095U, 4096U, 4097U, 16383U, 16384U, 16385U,
        65535U, 65536U, 65537U, 131073U, 262145U
    };
    if (value % 8U == 0U) return edges[(value >> 4U) % (sizeof(edges) / sizeof(edges[0]))];
    return (size_t)((value >> 8U) % 8193U);
}

static void *mixed(void *argument)
{
    context *ctx = argument;
    object slots[SLOTS] = {{0}};
    size_t operation;
    for (operation = 0U; operation < ctx->operations; ++operation) {
        const uint32_t value = next_random(&ctx->seed);
        object *item = &slots[value % SLOTS];
        const size_t size = varied_size(next_random(&ctx->seed));
        if (item->ptr == NULL) {
            item->ptr = value % 4U == 0U ? my_calloc(size, 1U) : my_malloc(size);
            REQUIRE(item->ptr != NULL);
            item->size = size;
            if (value % 4U == 0U) {
                size_t index;
                for (index = 0U; index < size; ++index) REQUIRE(item->ptr[index] == 0U);
            }
            item->tag = (unsigned char)(value >> 24U);
            fill(item);
        } else {
            verify(item, item->size);
            if (value % 3U == 0U) {
                my_free(item->ptr);
                item->ptr = NULL;
            } else {
                unsigned char *replacement = my_realloc(item->ptr, size);
                if (size == 0U) {
                    REQUIRE(replacement == NULL);
                } else {
                    REQUIRE(replacement != NULL);
                    item->ptr = replacement;
                    verify(item, item->size < size ? item->size : size);
                }
                item->ptr = replacement;
                item->size = size;
                if (replacement != NULL) fill(item);
            }
        }
        if (operation % 8192U == 0U) memctl_trim();
    }
    for (operation = 0U; operation < SLOTS; ++operation) {
        if (slots[operation].ptr != NULL) {
            verify(&slots[operation], slots[operation].size);
            my_free(slots[operation].ptr);
        }
    }
    return NULL;
}

static void *transfer(void *argument)
{
    context *ctx = argument;
    size_t round;
    size_t index;
    object *row = handoff[ctx->id];
    for (index = 0U; index < SLOTS; ++index) {
        row[index].size = 97U + index * 29U;
        row[index].tag = (unsigned char)(index + ctx->id);
        row[index].ptr = my_malloc(row[index].size);
        REQUIRE(row[index].ptr != NULL);
        fill(&row[index]);
    }
    for (round = 0U; round < transfer_rounds; ++round) {
        (void)pthread_barrier_wait(&barrier);
        row = handoff[(ctx->id + round + 1U) % WORKERS];
        for (index = 0U; index < SLOTS; ++index) {
            object *item = &row[index];
            const size_t size = 1U + next_random(&ctx->seed) % 32769U;
            unsigned char *replacement;
            verify(item, item->size);
            if ((round + index) % 5U == 0U) {
                my_free(item->ptr);
                item->ptr = my_malloc(size);
                REQUIRE(item->ptr != NULL);
            } else {
                replacement = my_realloc(item->ptr, size);
                REQUIRE(replacement != NULL);
                item->ptr = replacement;
                verify(item, item->size < size ? item->size : size);
            }
            item->size = size;
            ++item->tag;
            fill(item);
        }
        if (round % 16U == 0U) memctl_trim();
    }
    (void)pthread_barrier_wait(&barrier);
    for (index = 0U; index < SLOTS; ++index) {
        verify(&row[index], row[index].size);
        my_free(row[index].ptr);
    }
    return NULL;
}

static unsigned long number(const char *text)
{
    char *end;
    unsigned long result;
    errno = 0;
    result = strtoul(text, &end, 10);
    REQUIRE(errno == 0 && end != text && *end == '\0' && result > 0UL && result <= UINT32_MAX);
    return result;
}

int main(int argc, char **argv)
{
    pthread_t threads[WORKERS];
    context contexts[WORKERS];
    size_t index;
    unsigned int phase;
    const size_t operations = argc > 1 ? (size_t)number(argv[1]) : 125000U;
    const uint32_t seed = argc > 2 ? (uint32_t)number(argv[2]) : UINT32_C(20261109);
    REQUIRE(operations <= 10000000U && argc <= 4);
    if (argc > 3) transfer_rounds = (size_t)number(argv[3]);
    REQUIRE(transfer_rounds <= 4096U);
    REQUIRE(pthread_barrier_init(&barrier, NULL, WORKERS) == 0);
    for (phase = 0U; phase < 2U; ++phase) {
        for (index = 0U; index < WORKERS; ++index) {
            contexts[index].id = index;
            contexts[index].operations = operations;
            contexts[index].seed = seed ^ ((uint32_t)index + 1U) * UINT32_C(0x9E3779B9);
            if (contexts[index].seed == 0U) contexts[index].seed = 1U;
            REQUIRE(pthread_create(&threads[index], NULL, phase == 0U ? mixed : transfer, &contexts[index]) == 0);
        }
        for (index = 0U; index < WORKERS; ++index) REQUIRE(pthread_join(threads[index], NULL) == 0);
        (void)printf("PASS %s seed=%" PRIu32 "\n", phase == 0U ? "mixed full-pattern soak" : "synchronized ownership handoffs", seed);
    }
    memctl_trim();
    REQUIRE(pthread_barrier_destroy(&barrier) == 0);
    (void)printf("PASS %zu mixed operations plus %zu handoffs\n", operations * WORKERS, transfer_rounds * WORKERS * SLOTS);
    return 0;
}
