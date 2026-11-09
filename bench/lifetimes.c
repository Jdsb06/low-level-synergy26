#include "profile.h"

#include <pthread.h>

#define WORKERS 8U
#ifdef MEMCTL_LARGE_LIFETIMES
#define SLOTS 64U
#else
#define SLOTS 512U
#endif
#define CLASSES 64U
#define CYCLES 3U

typedef struct object {
    unsigned char *ptr;
    size_t size;
} object;

static object objects[WORKERS][SLOTS];
static pthread_barrier_t begin;
static pthread_barrier_t end;
static unsigned int command;

static size_t request_size(size_t index)
{
#ifdef MEMCTL_LARGE_LIFETIMES
    return 65537U + index * 1024U;
#else
    if (index < 16U) return (index + 1U) * 16U;
    if (index < 28U) return 256U + (index - 15U) * 64U;
    if (index < 40U) return 1024U + (index - 27U) * 256U;
    if (index < 52U) return 4096U + (index - 39U) * 1024U;
    return 16384U + (index - 51U) * 4096U;
#endif
}

static void verify(const object *item, unsigned char tag)
{
    size_t offset;
    for (offset = 0; offset < item->size; ++offset) require(item->ptr[offset] == tag);
}

static void *worker(void *argument)
{
    const size_t id = *(const size_t *)argument;
    unsigned int phase;
    for (;;) {
        size_t index;
        (void)pthread_barrier_wait(&begin);
        phase = command;
        if (phase == 5U) break;
        for (index = 0; index < SLOTS; ++index) {
            object *item = &objects[id][index];
            const int survivor = (index / CLASSES + index % CLASSES) % 8U == 0;
            if ((phase == 1U || phase == 3U) && item->ptr == NULL) {
                item->size = request_size((index + (phase == 3U ? 17U : 0U)) % CLASSES);
                item->ptr = ALLOC(item->size);
                require(item->ptr != NULL);
                /* Touch every requested byte, not just allocation metadata. */
                memset(item->ptr, (int)(id + 1U), item->size);
            } else if (item->ptr != NULL && ((phase == 2U && !survivor) || phase == 4U)) {
                verify(item, (unsigned char)(id + 1U));
                RELEASE(item->ptr);
                item->ptr = NULL;
                item->size = 0;
            } else if (item->ptr != NULL) {
                verify(item, (unsigned char)(id + 1U));
            }
        }
        (void)pthread_barrier_wait(&end);
    }
    return NULL;
}

static void phase(unsigned int value)
{
    command = value;
    (void)pthread_barrier_wait(&begin);
    (void)pthread_barrier_wait(&end);
}

static unsigned long status_kib(const char *key)
{
    FILE *file = fopen("/proc/self/status", "r");
    char line[256];
    unsigned long value = 0;
    int found = 0;
    require(file != NULL);
    while (fgets(line, sizeof(line), file) != NULL) {
        if (strncmp(line, key, strlen(key)) == 0) {
            require(sscanf(line + strlen(key), "%lu", &value) == 1);
            found = 1;
            break;
        }
    }
    require(fclose(file) == 0 && found);
    return value;
}

static unsigned long resident_kib(void)
{
    FILE *file = fopen("/proc/self/smaps_rollup", "r");
    char line[256];
    unsigned long value = 0;
    int found = 0;
    require(file != NULL);
    while (fgets(line, sizeof(line), file) != NULL) {
        if (sscanf(line, "Rss: %lu", &value) == 1) {
            found = 1;
            break;
        }
    }
    require(fclose(file) == 0 && found);
    return value;
}

static void snapshot(unsigned int cycle, const char *label, int first)
{
    size_t live = 0;
    size_t count = 0;
    size_t thread;
    size_t index;
    for (thread = 0; thread < WORKERS; ++thread) {
        for (index = 0; index < SLOTS; ++index) {
            live += objects[thread][index].size;
            count += objects[thread][index].ptr != NULL;
        }
    }
    printf("%s{\"cycle\":%u,\"phase\":\"%s\",\"live_bytes\":%zu,\"live_objects\":%zu,"
           "\"vm_kib\":%lu,\"rss_kib\":%lu,\"rss_rollup_kib\":%lu,\"vm_peak_kib\":%lu,\"vm_hwm_kib\":%lu}",
           first ? "" : ",", cycle, label, live, count, status_kib("VmSize:"),
           status_kib("VmRSS:"), resident_kib(), status_kib("VmPeak:"), status_kib("VmHWM:"));
}

int main(void)
{
    pthread_t threads[WORKERS];
    size_t ids[WORKERS];
    size_t index;
    unsigned int cycle;
    memset(objects, 0, sizeof(objects));
    /* Warm only harness proc parsers, not worker allocators. Keep workers alive
       in every measured phase; first-use allocator arenas count above idle. */
    require(setvbuf(stdout, NULL, _IONBF, 0) == 0);
    (void)status_kib("VmSize:");
    (void)resident_kib();
    require(pthread_barrier_init(&begin, NULL, WORKERS + 1U) == 0);
    require(pthread_barrier_init(&end, NULL, WORKERS + 1U) == 0);
    for (index = 0; index < WORKERS; ++index) {
        ids[index] = index;
        require(pthread_create(&threads[index], NULL, worker, &ids[index]) == 0);
    }
    phase(0);
    fputs("{\"correct\":true,\"workers\":8,\"snapshots\":[", stdout);
    snapshot(0, "idle", 1);
    for (cycle = 1; cycle <= CYCLES; ++cycle) {
        phase(1);
        snapshot(cycle, "burst", 0);
        phase(2);
        snapshot(cycle, "sparse", 0);
        phase(3);
        snapshot(cycle, "refill", 0);
        phase(4);
        snapshot(cycle, "freed", 0);
        profile_trim();
        snapshot(cycle, "trimmed", 0);
    }
    command = 5;
    (void)pthread_barrier_wait(&begin);
    for (index = 0; index < WORKERS; ++index) require(pthread_join(threads[index], NULL) == 0);
    require(pthread_barrier_destroy(&begin) == 0);
    require(pthread_barrier_destroy(&end) == 0);
    puts("]}");
    return 0;
}
