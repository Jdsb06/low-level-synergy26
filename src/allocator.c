#include "libmemctl.h"

#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#ifndef MEMCTL_SHARDS
#define MEMCTL_SHARDS 8U
#endif
#define CLASS_COUNT 64U
#define SMALL_LIMIT 65536U
#ifndef MEMCTL_REGION_MIN
#define MEMCTL_REGION_MIN 16384U
#endif
#ifndef MEMCTL_INITIAL_BLOCKS
#define MEMCTL_INITIAL_BLOCKS 4U
#endif
#define CACHE_LIMIT (2U * 1024U * 1024U)
#define CACHE_REGION_LIMIT 65536U

typedef struct region region;
typedef struct bin bin;

typedef struct block_header {
    region *owner;
    size_t requested;
} block_header;

struct region {
    bin *owner;
    region *prev;
    region *next;
    block_header *free_head;
    size_t mapping_bytes;
    size_t capacity;
    size_t free_count;
    size_t total_count;
};

struct bin {
    pthread_mutex_t lock;
    region *available;
    region *cached;
    unsigned int region_count;
    unsigned int busy;
};

_Static_assert(MEMCTL_SHARDS > 0U, "at least one shard required");
_Static_assert(MEMCTL_INITIAL_BLOCKS > 0U && MEMCTL_INITIAL_BLOCKS <= 32U,
               "initial block target must be in 1..32");
_Static_assert(sizeof(block_header) % _Alignof(max_align_t) == 0U,
               "block header must preserve max alignment on this target");

static _Alignas(64) bin bins[MEMCTL_SHARDS][CLASS_COUNT];
static pthread_once_t once = PTHREAD_ONCE_INIT;
static size_t page_size;
static int init_error;
static atomic_uint next_shard;
static atomic_size_t cached_bytes;
static _Thread_local unsigned int thread_shard;
static _Thread_local int shard_assigned;

static void initialize(void)
{
    const long discovered = sysconf(_SC_PAGESIZE);
    unsigned int shard;
    unsigned int index;
    if (discovered <= 0) {
        init_error = EINVAL;
        return;
    }
    page_size = (size_t)discovered;
    for (shard = 0U; shard < MEMCTL_SHARDS; ++shard) {
        for (index = 0U; index < CLASS_COUNT; ++index) {
            const int error = pthread_mutex_init(&bins[shard][index].lock, NULL);
            if (error != 0) {
                init_error = error;
                return;
            }
        }
    }
}

static size_t align_up(size_t value, size_t alignment)
{
    return ((value + alignment - 1U) / alignment) * alignment;
}

/* Checked separately from the small, statically bounded slab calculations. */
static int mapping_size(size_t payload, size_t overhead, size_t *result)
{
    size_t total;
    if (payload > SIZE_MAX - overhead) {
        errno = ENOMEM;
        return -1;
    }
    total = payload + overhead;
    if (total > SIZE_MAX - (page_size - 1U)) {
        errno = ENOMEM;
        return -1;
    }
    *result = align_up(total, page_size);
    return 0;
}

static size_t region_offset(void)
{
    return align_up(sizeof(region), _Alignof(max_align_t));
}

static unsigned int size_class(size_t size, size_t *capacity)
{
    unsigned int index;
    if (size <= 256U) {
        index = (unsigned int)((size - 1U) / 16U);
        *capacity = ((size_t)index + 1U) * 16U;
    } else if (size <= 1024U) {
        index = 16U + (unsigned int)((size - 257U) / 64U);
        *capacity = 256U + ((size_t)index - 15U) * 64U;
    } else if (size <= 4096U) {
        index = 28U + (unsigned int)((size - 1025U) / 256U);
        *capacity = 1024U + ((size_t)index - 27U) * 256U;
    } else if (size <= 16384U) {
        index = 40U + (unsigned int)((size - 4097U) / 1024U);
        *capacity = 4096U + ((size_t)index - 39U) * 1024U;
    } else {
        index = 52U + (unsigned int)((size - 16385U) / 4096U);
        *capacity = 16384U + ((size_t)index - 51U) * 4096U;
    }
    return index;
}

static void add_available(bin *owner, region *item)
{
    item->prev = NULL;
    item->next = owner->available;
    if (item->next != NULL) {
        item->next->prev = item;
    }
    owner->available = item;
}

static void remove_available(bin *owner, region *item)
{
    if (item->prev != NULL) {
        item->prev->next = item->next;
    } else {
        owner->available = item->next;
    }
    if (item->next != NULL) {
        item->next->prev = item->prev;
    }
}

static region *new_region(bin *owner, size_t capacity)
{
    const size_t stride = sizeof(block_header) + capacity;
    const size_t offset = region_offset();
    size_t blocks = MEMCTL_INITIAL_BLOCKS;
    size_t bytes;
    size_t index;
    region *item;
    if (owner->region_count == UINT_MAX) {
        errno = ENOMEM;
        return NULL;
    }
    /* Start compact for sparse classes. Once an existing region fills, remember
       the demonstrated demand even after quiescence, avoiding repeated small
       mapping churn in hot classes. No timing or workload fingerprint is used. */
    if (owner->region_count != 0U) owner->busy = 1;
    if (owner->busy) blocks = 32U;
    if (mapping_size(stride * blocks, offset, &bytes) != 0) {
        return NULL;
    }
    if (bytes < MEMCTL_REGION_MIN) {
        bytes = align_up(MEMCTL_REGION_MIN, page_size);
    }
    item = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (item == MAP_FAILED) {
        return NULL;
    }
    item->owner = owner;
    item->mapping_bytes = bytes;
    item->capacity = capacity;
    item->total_count = (bytes - offset) / stride;
    item->free_count = item->total_count;
    item->free_head = NULL;
    ++owner->region_count;
    for (index = 0U; index < item->total_count; ++index) {
        block_header *header = (block_header *)((unsigned char *)item + offset + index * stride);
        header->owner = item;
        *(block_header **)(void *)(header + 1) = item->free_head;
        item->free_head = header;
    }
    add_available(owner, item);
    return item;
}

static int reserve_cache(size_t bytes)
{
    size_t previous = atomic_load_explicit(&cached_bytes, memory_order_relaxed);
    while (previous <= CACHE_LIMIT && bytes <= CACHE_LIMIT - previous) {
        if (atomic_compare_exchange_weak_explicit(&cached_bytes, &previous,
                                                  previous + bytes,
                                                  memory_order_relaxed,
                                                  memory_order_relaxed)) {
            return 1;
        }
    }
    return 0;
}

void *my_malloc(size_t size)
{
    const size_t payload = size == 0U ? 1U : size;
    block_header *header;
    region *item;
    size_t capacity;
    unsigned int index;
    bin *owner;
    const int once_error = pthread_once(&once, initialize);
    if (once_error != 0 || init_error != 0) {
        errno = once_error != 0 ? once_error : init_error;
        return NULL;
    }
    if (payload > SMALL_LIMIT) {
        size_t bytes;
        const size_t overhead = region_offset() + sizeof(block_header);
        if (mapping_size(payload, overhead, &bytes) != 0) {
            return NULL;
        }
        item = mmap(NULL, bytes, PROT_READ | PROT_WRITE,
                    MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (item == MAP_FAILED) {
            return NULL;
        }
        item->owner = NULL;
        item->mapping_bytes = bytes;
        item->capacity = bytes - overhead;
        header = (block_header *)((unsigned char *)item + region_offset());
        header->owner = item;
        header->requested = size;
        return header + 1;
    }
    if (!shard_assigned) {
        thread_shard = atomic_fetch_add_explicit(&next_shard, 1U,
                                                 memory_order_relaxed) % MEMCTL_SHARDS;
        shard_assigned = 1;
    }
    index = size_class(payload, &capacity);
    owner = &bins[thread_shard][index];
    (void)pthread_mutex_lock(&owner->lock);
    item = owner->available;
    /* A bin creates at most one undersized starter region. Once it is busy,
       stop refilling that region so its live objects can drain naturally. */
    if (item != NULL && owner->busy && item->total_count < 32U) item = item->next;
    if (item == NULL) {
        item = new_region(owner, capacity);
        if (item == NULL) {
            const int saved = errno;
            (void)pthread_mutex_unlock(&owner->lock);
            errno = saved;
            return NULL;
        }
    }
    if (owner->cached == item) {
        owner->cached = NULL;
        (void)atomic_fetch_sub_explicit(&cached_bytes, item->mapping_bytes,
                                        memory_order_relaxed);
    }
    header = item->free_head;
    item->free_head = *(block_header **)(void *)(header + 1);
    --item->free_count;
    if (item->free_count == 0U) {
        remove_available(owner, item);
    }
    header->requested = size;
    (void)pthread_mutex_unlock(&owner->lock);
    return header + 1;
}

void my_free(void *ptr)
{
    block_header *header;
    region *item;
    bin *owner;
    const int saved = errno;
    if (ptr == NULL) {
        return;
    }
    header = (block_header *)ptr - 1;
    item = header->owner;
    owner = item->owner;
    if (owner == NULL) {
        (void)munmap(item, item->mapping_bytes);
        errno = saved;
        return;
    }
    (void)pthread_mutex_lock(&owner->lock);
    if (item->free_count == 0U) {
        add_available(owner, item);
    }
    *(block_header **)ptr = item->free_head;
    item->free_head = header;
    ++item->free_count;
    if (item->free_count == item->total_count) {
        if (owner->cached == NULL && (!owner->busy || item->total_count >= 32U) &&
            item->mapping_bytes <= CACHE_REGION_LIMIT &&
            reserve_cache(item->mapping_bytes)) {
            owner->cached = item;
        } else {
            remove_available(owner, item);
            --owner->region_count;
            (void)munmap(item, item->mapping_bytes);
        }
    }
    (void)pthread_mutex_unlock(&owner->lock);
    errno = saved;
}

void *my_realloc(void *ptr, size_t size)
{
    block_header *header;
    size_t previous;
    void *replacement;
    if (ptr == NULL) {
        return my_malloc(size);
    }
    if (size == 0U) {
        my_free(ptr);
        return NULL;
    }
    header = (block_header *)ptr - 1;
    previous = header->requested;
    /* Caller owns this live block; region capacity is immutable. Avoid retaining
       a huge mapping after a substantial shrink. */
    if (size <= header->owner->capacity && size >= header->owner->capacity / 2U) {
        header->requested = size;
        return ptr;
    }
    replacement = my_malloc(size);
    if (replacement == NULL) {
        return NULL;
    }
    (void)memcpy(replacement, ptr, previous < size ? previous : size);
    my_free(ptr);
    return replacement;
}

void *my_calloc(size_t nmemb, size_t size)
{
    size_t bytes;
    void *ptr;
    if (size != 0U && nmemb > SIZE_MAX / size) {
        errno = ENOMEM;
        return NULL;
    }
    bytes = nmemb * size;
    ptr = my_malloc(bytes);
    if (ptr != NULL && bytes != 0U) {
        (void)memset(ptr, 0, bytes);
    }
    return ptr;
}

void memctl_trim(void)
{
    unsigned int shard;
    unsigned int index;
    const int saved = errno;
    if (pthread_once(&once, initialize) != 0 || init_error != 0) {
        return;
    }
    for (shard = 0U; shard < MEMCTL_SHARDS; ++shard) {
        for (index = 0U; index < CLASS_COUNT; ++index) {
            bin *owner = &bins[shard][index];
            region *item;
            (void)pthread_mutex_lock(&owner->lock);
            item = owner->cached;
            if (item != NULL) {
                remove_available(owner, item);
                owner->cached = NULL;
                --owner->region_count;
                (void)atomic_fetch_sub_explicit(&cached_bytes, item->mapping_bytes,
                                                memory_order_relaxed);
                (void)munmap(item, item->mapping_bytes);
            }
            (void)pthread_mutex_unlock(&owner->lock);
        }
    }
    errno = saved;
}
