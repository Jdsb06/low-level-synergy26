#include "libmemctl.h"

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WORKERS 8U
#define CLASSES 64U
static void *objects[WORKERS][CLASSES];

static size_t request_size(unsigned int index)
{
    if (index < 16U) return (index + 1U) * 16U;
    if (index < 28U) return 256U + (index - 15U) * 64U;
    if (index < 40U) return 1024U + (index - 27U) * 256U;
    if (index < 52U) return 4096U + (index - 39U) * 1024U;
    return 16384U + (index - 51U) * 4096U;
}

static void *allocate(void *argument)
{
    const size_t worker = *(const size_t *)argument;
    unsigned int index;
    for (index = 0U; index < CLASSES; ++index) {
        const size_t size = request_size(index);
        objects[worker][index] = my_malloc(size);
        if (objects[worker][index] == NULL) exit(2);
        (void)memset(objects[worker][index], (int)(worker + 1U), size);
    }
    return NULL;
}

static void allocation_wave(void)
{
    pthread_t threads[WORKERS];
    size_t ids[WORKERS];
    unsigned int index;
    for (index = 0U; index < WORKERS; ++index) {
        ids[index] = index;
        if (pthread_create(&threads[index], NULL, allocate, &ids[index]) != 0) exit(2);
    }
    for (index = 0U; index < WORKERS; ++index) {
        if (pthread_join(threads[index], NULL) != 0) exit(2);
    }
}

static size_t release_wave(void)
{
    unsigned int worker;
    unsigned int index;
    size_t payload = 0U;
    for (worker = 0U; worker < WORKERS; ++worker) {
        for (index = 0U; index < CLASSES; ++index) {
            const unsigned char *ptr = objects[worker][index];
            const size_t size = request_size(index);
            size_t offset;
            payload += size;
            for (offset = 0U; offset < size; ++offset) {
                if (ptr[offset] != (unsigned char)(worker + 1U)) exit(3);
            }
            my_free(objects[worker][index]);
        }
    }
    return payload;
}

static unsigned long vm_kib(void)
{
    FILE *file = fopen("/proc/self/status", "r");
    char line[256];
    unsigned long value = 0UL;
    if (file == NULL) exit(2);
    while (fgets(line, sizeof(line), file) != NULL) {
        if (sscanf(line, "VmSize: %lu", &value) == 1) break;
    }
    if (fclose(file) != 0 || value == 0UL) exit(2);
    return value;
}

int main(void)
{
    unsigned long idle;
    unsigned long held;
    unsigned long trimmed;
    size_t payload;
    /* Warm pthread's stack cache so it is included in both process samples. */
    allocation_wave();
    (void)release_wave();
    memctl_trim();
    idle = vm_kib();
    allocation_wave();
    held = vm_kib();
    payload = release_wave();
    memctl_trim();
    trimmed = vm_kib();
    (void)printf("{\"payload_bytes\":%zu,\"idle_vm_kib\":%lu,"
                 "\"held_vm_kib\":%lu,\"trimmed_vm_kib\":%lu,\"correct\":true}\n",
                 payload, idle, held, trimmed);
    return 0;
}
