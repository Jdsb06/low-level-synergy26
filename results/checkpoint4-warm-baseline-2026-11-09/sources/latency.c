#include "profile.h"

#include <inttypes.h>
#include <pthread.h>
#include <time.h>

#define WORKERS 8U
#define SLOTS 128U
#define APIS 4U

typedef struct sample {
    uint64_t ns;
    unsigned int api;
} sample;

typedef struct object {
    unsigned char *ptr;
    size_t size;
    unsigned char tag;
} object;

typedef struct context {
    size_t operations;
    uint32_t seed;
    int kind;
    sample *samples;
} context;

static pthread_barrier_t start;

static uint64_t now_ns(void)
{
    struct timespec stamp;
    require(clock_gettime(CLOCK_MONOTONIC, &stamp) == 0);
    return (uint64_t)stamp.tv_sec * UINT64_C(1000000000) + (uint64_t)stamp.tv_nsec;
}

static size_t request_size(uint32_t value, int kind)
{
    static const size_t mixed[] = {
        1, 17, 33, 255, 256, 257, 1024, 1025, 4096, 4097,
        16384, 16385, 65535, 65536, 65537, 131072
    };
    if (kind == 0) return 33U;
    if (kind == 2) return 65537U + value % 65536U;
    return mixed[value % (sizeof(mixed) / sizeof(mixed[0]))];
}

static void verify(const object *item, size_t prefix)
{
    size_t index;
    const size_t checked = prefix < 32U ? prefix : 32U;
    for (index = 0; index < checked; ++index) require(item->ptr[index] == item->tag);
    if (prefix == item->size) require(item->ptr[item->size - 1U] == item->tag);
}

static void fill(object *item)
{
    memset(item->ptr, item->tag, item->size < 32U ? item->size : 32U);
    item->ptr[item->size - 1U] = item->tag;
}

static void trace(context *ctx, object *slots, size_t count, int measured)
{
    size_t index;
    for (index = 0; index < count; ++index) {
        const uint32_t value = random_next(&ctx->seed);
        object *item = &slots[value % SLOTS];
        const size_t size = request_size(value >> 8U, ctx->kind);
        uint64_t before;
        uint64_t elapsed;
        unsigned int api;
        unsigned char *result;
        if (item->ptr == NULL) {
            const int zeroed = ctx->kind != 0 && ((value >> 20U) & 1U) != 0;
            api = zeroed ? 3U : 0U;
            before = measured ? now_ns() : 0;
            result = zeroed ? ZERO_ALLOC(1, size) : ALLOC(size);
            elapsed = measured ? now_ns() - before : 0;
            require(result != NULL);
            if (zeroed) require(result[0] == 0 && result[size - 1U] == 0);
            item->ptr = result;
            item->size = size;
            item->tag = (unsigned char)(value >> 24U);
        } else {
            verify(item, item->size);
            if (ctx->kind != 0 && ((value >> 16U) & 3U) == 0) {
                const size_t preserved = size < item->size ? size : item->size;
                api = 2;
                before = measured ? now_ns() : 0;
                result = RESIZE(item->ptr, size);
                elapsed = measured ? now_ns() - before : 0;
                require(result != NULL);
                item->ptr = result;
                verify(item, preserved);
                item->size = size;
            } else {
                api = 1;
                before = measured ? now_ns() : 0;
                RELEASE(item->ptr);
                elapsed = measured ? now_ns() - before : 0;
                item->ptr = NULL;
            }
        }
        if (item->ptr != NULL) fill(item);
        if (measured) ctx->samples[index] = (sample){elapsed, api};
    }
}

static void release_slots(object *slots)
{
    size_t index;
    for (index = 0; index < SLOTS; ++index) {
        if (slots[index].ptr != NULL) verify(&slots[index], slots[index].size);
        RELEASE(slots[index].ptr);
        slots[index].ptr = NULL;
    }
}

static void *worker(void *argument)
{
    context *ctx = argument;
    object slots[SLOTS] = {{0}};
    const uint32_t measured_seed = ctx->seed;
    trace(ctx, slots, 2000, 0);
    release_slots(slots);
    ctx->seed = measured_seed;
    (void)pthread_barrier_wait(&start);
    trace(ctx, slots, ctx->operations, 1);
    release_slots(slots);
    return NULL;
}

static int compare_sample(const void *left, const void *right)
{
    const sample *a = left;
    const sample *b = right;
    if (a->api != b->api) return a->api < b->api ? -1 : 1;
    return a->ns < b->ns ? -1 : a->ns > b->ns;
}

static uint64_t percentile(const sample *items, size_t count, size_t per_mille)
{
    /* Nearest rank: ceil(count * fraction), with no interpolation. */
    return items[(count * per_mille + 999U) / 1000U - 1U].ns;
}

int main(int argc, char **argv)
{
    static const char *names[] = {"malloc", "free", "realloc", "calloc"};
    pthread_t threads[WORKERS];
    context contexts[WORKERS];
    sample clock_samples[10000];
    sample *samples;
    size_t operations;
    size_t total;
    size_t index;
    size_t offset = 0;
    unsigned int workers;
    unsigned int api;
    int kind;
    int printed = 0;
    require(argc == 5);
    workers = (unsigned int)number(argv[1], WORKERS);
    operations = (size_t)number(argv[2], 1000000);
    kind = strcmp(argv[4], "hot") == 0 ? 0 : strcmp(argv[4], "mixed") == 0 ? 1 : 2;
    require(kind != 2 || strcmp(argv[4], "large") == 0);
    total = workers * operations;
    samples = calloc(total, sizeof(*samples));
    require(samples != NULL);
    /* Pre-touch sample storage; this is harness memory, never allocator payload. */
    memset(samples, 0, total * sizeof(*samples));
    for (index = 0; index < 10000; ++index) {
        const uint64_t before = now_ns();
        clock_samples[index] = (sample){now_ns() - before, 0};
    }
    qsort(clock_samples, 10000, sizeof(*clock_samples), compare_sample);
    require(pthread_barrier_init(&start, NULL, workers + 1U) == 0);
    for (index = 0; index < workers; ++index) {
        contexts[index] = (context){operations,
            (uint32_t)number(argv[3], UINT32_MAX) ^ ((uint32_t)index + 1U) * UINT32_C(0x9e3779b9),
            kind, samples + index * operations};
        if (contexts[index].seed == 0) contexts[index].seed = 1;
        require(pthread_create(&threads[index], NULL, worker, &contexts[index]) == 0);
    }
    (void)pthread_barrier_wait(&start);
    for (index = 0; index < workers; ++index) require(pthread_join(threads[index], NULL) == 0);
    require(pthread_barrier_destroy(&start) == 0);
    qsort(samples, total, sizeof(*samples), compare_sample);
    printf("{\"correct\":true,\"threads\":%u,\"samples\":%zu,\"clock_pair_p50_ns\":%" PRIu64
           ",\"clock_pair_p99_ns\":%" PRIu64 ",\"apis\":{",
           workers, total, percentile(clock_samples, 10000, 500), percentile(clock_samples, 10000, 990));
    for (api = 0; api < APIS; ++api) {
        const size_t first = offset;
        while (offset < total && samples[offset].api == api) ++offset;
        if (offset != first) {
            const size_t count = offset - first;
            printf("%s\"%s\":{\"count\":%zu,\"p50_ns\":%" PRIu64 ",\"p95_ns\":%" PRIu64
                   ",\"p99_ns\":%" PRIu64 ",\"p999_ns\":%" PRIu64 ",\"max_ns\":%" PRIu64 "}",
                   printed ? "," : "", names[api], count, percentile(samples + first, count, 500),
                   percentile(samples + first, count, 950), percentile(samples + first, count, 990),
                   percentile(samples + first, count, 999), samples[offset - 1U].ns);
            printed = 1;
        }
    }
    puts("}}");
    free(samples);
    profile_trim();
    return 0;
}
